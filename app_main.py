#!/usr/bin/env python3
"""Frozen / desktop entry point for the Gradio UI."""

from __future__ import annotations

import os
import socket
import sys
import traceback
from pathlib import Path


def _ensure_stdio() -> None:
    """PyInstaller windowed builds set stdout/stderr to None.

    uvicorn logging then crashes with:
      AttributeError: 'NoneType' object has no attribute 'isatty'
      Unable to configure formatter 'default'
    """
    log_path = None
    try:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        log_dir = base / "jht-po-styles"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "app.log"
    except Exception:
        log_path = None

    def _open_fallback():
        if log_path is not None:
            try:
                return open(log_path, "a", encoding="utf-8", buffering=1)
            except Exception:
                pass
        return open(os.devnull, "w", encoding="utf-8")

    if sys.stdout is None:
        sys.stdout = _open_fallback()
    if sys.stderr is None:
        sys.stderr = _open_fallback()


# Must run before importing gradio/uvicorn (stdio may be None in frozen GUI apps).
_ensure_stdio()


def _free_port(preferred: int = 7860) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def _log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    path = base / "jht-po-styles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_crash_log(text: str) -> Path:
    log = _log_dir() / "crash.log"
    log.write_text(text, encoding="utf-8")
    return log


def _show_error(title: str, message: str) -> None:
    """Show a visible error on Windows even when packaged without a console."""
    print(message, file=sys.stderr)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message[:1024], title, 0x10)  # MB_ICONERROR
        except Exception:
            pass


def _warn_non_ascii_path() -> None:
    """PyInstaller + some native deps are unreliable under non-ASCII install paths."""
    try:
        exe = Path(sys.executable).resolve()
        s = str(exe)
        if any(ord(ch) > 127 for ch in s):
            _show_error(
                "路径包含中文/特殊字符",
                "请把整个 JhtPoStyles 文件夹复制到纯英文路径后再打开，例如：\n"
                "C:\\Tools\\JhtPoStyles\\\n\n"
                f"当前路径：\n{s}",
            )
    except Exception:
        pass


def main() -> None:
    # Gradio / analytics / SSR — keep packaging simple (no Node required)
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("GRADIO_SSR_MODE", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    _warn_non_ascii_path()

    # Must run before importing playwright-using modules in some packagers
    from jht_po_styles import configure_playwright_browsers_path

    configure_playwright_browsers_path()

    from jht_po_ui import build

    port = int(os.environ.get("JHT_PO_PORT", _free_port()))
    demo = build()
    launch_kwargs = dict(
        server_name="127.0.0.1",
        server_port=port,
        inbrowser=True,
        show_error=True,
        quiet=False,
    )
    try:
        demo.launch(**launch_kwargs, ssr_mode=False)
    except TypeError:
        # Older Gradio without ssr_mode
        demo.launch(**launch_kwargs)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        tb = traceback.format_exc()
        try:
            log = _write_crash_log(tb)
            tip = f"\n\n详细日志已写入：\n{log}"
        except Exception:
            tip = ""
        _show_error("JhtPoStyles 启动失败", tb[-800:] + tip)
        sys.exit(1)
