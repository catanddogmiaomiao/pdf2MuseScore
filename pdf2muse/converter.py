from __future__ import annotations
import os
import json
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

@dataclass(frozen=True)
class ConversionResult:
    output: Path
    elapsed_seconds: float
    log_file: Path
    skipped_pages: tuple[int, ...] = ()

class ConversionError(RuntimeError):
    pass

class ConversionCancelled(ConversionError):
    pass

def convert_with_homr(pdf: Path, output_dir: Path, python: Path,
    on_log: Callable[[str], None] | None = None,
    on_stage: Callable[[str], None] | None = None,
    cancel: threading.Event | None = None) -> ConversionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / '.pdf2muse' / uuid.uuid4().hex
    run_dir.mkdir(parents=True)
    log_file = run_dir / 'homr.log'
    started = time.perf_counter()
    shutil.copy2(pdf, run_dir / 'score.pdf')
    command = [str(python.resolve()), '-u', str(Path(__file__).with_name('homr_runner.py').resolve())]
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    if on_stage:
        on_stage('正在准备模型和读取 PDF…')
    lines: queue.Queue[str | None] = queue.Queue()
    process = None
    with log_file.open('w', encoding='utf-8') as log:
        def emit(line: str) -> None:
            log.write(line + chr(10))
            log.flush()
            if on_log:
                on_log(line)
        emit(f'输入文件：{pdf}；任务目录：{run_dir}')
        emit('执行命令：' + subprocess.list2cmdline(command))
        try:
            if cancel and cancel.is_set():
                raise ConversionCancelled('已取消识别。')
            process = subprocess.Popen(command, cwd=run_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                encoding='utf-8', errors='replace',
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            def read() -> None:
                assert process is not None and process.stdout is not None
                try:
                    for line in process.stdout:
                        lines.put(line.rstrip())
                finally:
                    lines.put(None)
            reader = threading.Thread(target=read, daemon=True)
            reader.start()
            failed_page = False
            while True:
                if cancel and cancel.is_set():
                    raise ConversionCancelled('已取消识别。')
                try:
                    line = lines.get(timeout=.1)
                except queue.Empty:
                    continue
                if line is None:
                    break
                emit(line)
                failed_page |= 'An error occurred while processing' in line
                if on_stage:
                    if 'Downloading' in line or 'Downloaded' in line:
                        on_stage('首次使用：正在下载本地模型…')
                    elif 'Processing' in line or '================================' in line:
                        on_stage('正在识别页面中的乐谱…')
                    elif 'Finished ' in line:
                        on_stage('页面识别完成，正在继续处理…')
            code = process.wait()
            if cancel and cancel.is_set():
                raise ConversionCancelled('已取消识别。')
            if code or failed_page:
                raise ConversionError(f'HOMR 未完成整份乐谱的识别，请查看日志。日志：{log_file}')
            pages = [p for p in run_dir.glob('score_*.png') if re.fullmatch(r'score_[0-9]+\.png', p.name)]
            source = run_dir / ('score_0_merged.musicxml' if len(pages) > 1 else 'score_0.musicxml')
            if not source.is_file():
                raise ConversionError(f'没有找到完整的 MusicXML 输出。日志：{log_file}')
            root = ET.parse(source).getroot()
            if root.tag not in ('score-partwise', 'score-timewise') or not root.findall('.//note'):
                raise ConversionError(f'输出不包含可用的乐谱内容。日志：{log_file}')
            destination = output_dir / f'{pdf.stem}.musicxml'
            index = 2
            while destination.exists():
                destination = output_dir / f'{pdf.stem} ({index}).musicxml'
                index += 1
            shutil.copy2(source, destination)
            elapsed = time.perf_counter() - started
            emit(f'输出文件：{destination}；转换耗时：{elapsed:.2f} 秒')
            metadata = run_dir / 'pages.json'
            skipped = tuple(json.loads(metadata.read_text(encoding='utf-8'))['skipped']) if metadata.exists() else ()
            return ConversionResult(destination, elapsed, log_file, skipped)
        except ConversionError as exc:
            emit(str(exc))
            raise
        except (OSError, ET.ParseError) as exc:
            emit(str(exc))
            raise ConversionError(f'无法完成识别：{exc}；日志：{log_file}') from exc
        finally:
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                reader.join(timeout=2)
                if process.stdout:
                    process.stdout.close()
