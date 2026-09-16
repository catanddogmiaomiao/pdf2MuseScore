from __future__ import annotations

import re
import shutil
import subprocess
import time
import ctypes
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


def _physical_memory_gib() -> float:
    """Return installed physical memory without adding a third-party dependency."""
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_phys", ctypes.c_ulonglong),
            ("avail_phys", ctypes.c_ulonglong),
            ("total_page_file", ctypes.c_ulonglong),
            ("avail_page_file", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("avail_virtual", ctypes.c_ulonglong),
            ("avail_extended_virtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return 8.0
    return status.total_phys / (1024 ** 3)


def _configure_audiveris_memory(audiveris: Path) -> str | None:
    """Keep the JVM heap below RAM so Audiveris' native CV code has headroom.

    A heap equal to the machine's total RAM can make the JVM crash even while
    the Java heap is mostly empty, because OpenCV/JavaCPP and the JVM itself use
    native memory outside that heap.
    """
    config = audiveris.parent / "app" / "Audiveris.cfg"
    if not config.is_file():
        return None
    memory_gib = _physical_memory_gib()
    if memory_gib <= 10:
        heap_gib = 3
    elif memory_gib <= 16:
        heap_gib = 5
    elif memory_gib <= 24:
        heap_gib = 8
    else:
        heap_gib = min(12, max(8, int(memory_gib * 0.45)))
    try:
        original = config.read_text(encoding="utf-8")
        updated = re.sub(
            r"(?m)^java-options=-Xmx\S+\s*$",
            f"java-options=-Xmx{heap_gib}G",
            original,
        )
        updated = re.sub(
            r"(?m)^java-options=-Xms\S+\s*$",
            "java-options=-Xms256m",
            updated,
        )
        if updated != original:
            config.write_text(updated, encoding="utf-8")
        return f"Audiveris 内存配置：物理内存约 {memory_gib:.1f} GB，Java 上限 {heap_gib} GB"
    except OSError as exc:
        return f"警告：无法调整 Audiveris 内存配置（{exc}）"


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

    memory_notice = _configure_audiveris_memory(audiveris)
    if memory_notice:
        lines.append(memory_notice)
        if on_log:
            on_log(memory_notice)

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
