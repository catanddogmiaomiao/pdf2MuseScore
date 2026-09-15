from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class ConversionResult:
    output: Path
    elapsed_seconds: float
    log_file: Path


class ConversionError(RuntimeError):
    pass


def convert_with_audiveris(
    pdf: Path,
    output_dir: Path,
    audiveris: Path,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> ConversionResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = output_dir / ".pdf2muse" / f"{pdf.stem}-{time.strftime('%Y%m%d-%H%M%S')}"
    index = 2
    while run_dir.exists():
        run_dir = run_dir.with_name(f"{run_dir.name}-{index}")
        index += 1
    run_dir.mkdir(parents=True)
    log_file = output_dir / f"{pdf.stem}.audiveris.log"
    command = [
        str(audiveris), "-batch", "-transcribe", "-export", "-save",
        "-output", str(run_dir), "--", str(pdf),
    ]
    started = time.perf_counter()
    lines: list[str] = ["执行命令：" + subprocess.list2cmdline(command)]
    if on_log:
        on_log(lines[0])
    if on_progress:
        on_progress(8)

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise ConversionError(f"无法启动 Audiveris：{exc}") from exc

    assert process.stdout is not None
    progress = 10
    page_pattern = re.compile(r"(?:page|sheet)\D*(\d+)", re.IGNORECASE)
    for raw in process.stdout:
        line = raw.rstrip()
        if not line:
            continue
        lines.append(line)
        if on_log:
            on_log(line)
        if page_pattern.search(line):
            progress = min(88, progress + 5)
            if on_progress:
                on_progress(progress)

    return_code = process.wait()
    log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if return_code != 0:
        raise ConversionError(f"Audiveris 识别失败（退出代码 {return_code}），请查看日志。")

    candidates = sorted(
        [*run_dir.rglob("*.mxl"), *run_dir.rglob("*.musicxml"), *run_dir.rglob("*.xml")],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise ConversionError("Audiveris 已结束，但没有找到 MusicXML/MXL 输出。")

    source = candidates[0]
    suffix = ".mxl" if source.suffix.lower() == ".mxl" else ".musicxml"
    destination = output_dir / f"{pdf.stem}{suffix}"
    index = 2
    while destination.exists():
        destination = output_dir / f"{pdf.stem} ({index}){suffix}"
        index += 1
    shutil.move(str(source), destination)
    if on_progress:
        on_progress(100)
    return ConversionResult(destination, time.perf_counter() - started, log_file)
