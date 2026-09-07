#!/usr/bin/env python3
"""Frozen / desktop entry point for the Gradio UI."""

from __future__ import annotations

import os
import socket
import sys


def _free_port(preferred: int = 7860) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return preferred


def main() -> None:
    # Must run before importing playwright-using modules in some packagers
    from jht_po_styles import configure_playwright_browsers_path

    configure_playwright_browsers_path()

    from jht_po_ui import build

    port = int(os.environ.get("JHT_PO_PORT", _free_port()))
    demo = build()
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        inbrowser=True,
        show_error=True,
        quiet=False,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
