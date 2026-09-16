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
    skipped_pages: tuple[int, ...] = ()


class ConversionError(RuntimeError):
    pass


def _compact_page_ranges(pages: list[int]) -> list[str]:
    if not pages:
        return []
    ranges: list[str] = []
    start = previous = pages[0]
    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = page
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ranges


def _recoverable_pages(lines: list[str]) -> tuple[list[int], tuple[int, ...]]:
    text = "\n".join(lines)
    if "No regularly spaced lines found" not in text:
        return [], ()
    count_match = re.search(r"\b(\d+) sheets in ", text)
    invalid = tuple(sorted({int(value) for value in re.findall(r"#(\d+) flagged as invalid", text)}))
    if not count_match or not invalid:
        return [], ()
    total = int(count_match.group(1))
    valid = [page for page in range(1, total + 1) if page not in invalid]
    return valid, invalid


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
    started = time.perf_counter()
    lines: list[str] = []
    if on_progress:
        on_progress(8)

    def run_command(command: list[str], initial_progress: int, maximum_progress: int) -> int:
        command_line = "执行命令：" + subprocess.list2cmdline(command)
        lines.append(command_line)
        if on_log:
            on_log(command_line)
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
            log_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            raise ConversionError(f"无法启动 Audiveris：{exc}") from exc

        assert process.stdout is not None
        progress = initial_progress
        page_pattern = re.compile(r"(?:page|sheet)\D*(\d+)", re.IGNORECASE)
        for raw in process.stdout:
            line = raw.rstrip()
            if not line:
                continue
            lines.append(line)
            if on_log:
                on_log(line)
            if page_pattern.search(line):
                progress = min(maximum_progress, progress + 5)
                if on_progress:
                    on_progress(progress)
        return process.wait()

    command = [
        str(audiveris), "-batch", "-transcribe", "-export", "-save",
        "-output", str(run_dir), "--", str(pdf),
    ]
    return_code = run_command(command, 10, 88)
    valid_pages, skipped_pages = _recoverable_pages(lines) if return_code != 0 else ([], ())
    omr_files = sorted(run_dir.glob("*.omr"), key=lambda item: item.stat().st_mtime, reverse=True)
    if return_code != 0 and valid_pages and omr_files:
        ranges = _compact_page_ranges(valid_pages)
        notice = f"检测到无五线谱页面：{', '.join(map(str, skipped_pages))}；正在使用已保存的 OMR 工程恢复导出。"
        lines.extend(["", notice])
        if on_log:
            on_log(notice)
        if on_progress:
            on_progress(90)
        recovery_command = [
            str(audiveris), "-batch", "-transcribe", "-export", "-save",
            "-output", str(run_dir), "-sheets", *ranges, "--", str(omr_files[0]),
        ]
        return_code = run_command(recovery_command, 90, 98)

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
    return ConversionResult(destination, time.perf_counter() - started, log_file, skipped_pages)
