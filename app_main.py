#!/usr/bin/env python3
"""Frozen / desktop entry point for the Gradio UI."""

from __future__ import annotations

import inspect
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


def _dbg(hypothesis_id: str, message: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    # #region agent log
    import json
    import time

    payload = {
        "sessionId": "b5185c",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": "app_main.py",
        "message": message,
        "data": data or {},
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    targets = [
        Path("/Users/xuyucheng/Projects/jht-po-styles/.cursor/debug-b5185c.log"),
        _log_dir() / "debug-b5185c.log",
        Path.home() / "Desktop" / "debug-b5185c.log",
        Path.home() / "桌面" / "debug-b5185c.log",
    ]
    try:
        exe = Path(sys.executable).resolve()
        targets.append(exe.parent / "debug-b5185c.log")
    except Exception:
        pass
    for path in targets:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception:
            pass
    try:
        print(f"[dbg {hypothesis_id}] {message} {data}", file=sys.stderr)
    except Exception:
        pass
    # #endregion


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


def _bypass_proxy_for_localhost() -> None:
    """Windows system/HTTP proxies make Gradio's localhost self-check fail."""
    extras = "127.0.0.1,localhost,::1"
    for key in ("NO_PROXY", "no_proxy"):
        existing = os.environ.get(key, "").strip()
        os.environ[key] = f"{existing},{extras}" if existing else extras


def _patch_gradio_localhost_check() -> None:
    """Desktop EXE always serves 127.0.0.1; skip Gradio's optional self-HTTP probe."""
    try:
        import gradio.networking as networking

        networking.url_ok = lambda _url: True  # type: ignore[method-assign]
    except Exception:
        pass


def _patch_gradio_template_paths() -> None:
    """PyInstaller + importlib.resources makes Jinja look in a non-filesystem path.

    Runtime evidence: jinja2.environment.get_template during GET / (Windows EXE 500).
    """
    try:
        import gradio
        import gradio.routes as routes
        from starlette.templating import Jinja2Templates
    except Exception as exc:
        _dbg("B", "template patch import failed", {"type": type(exc).__name__, "msg": str(exc)})
        return

    templates_dir = Path(gradio.__file__).resolve().parent / "templates"
    index = templates_dir / "frontend" / "index.html"
    old = getattr(routes, "STATIC_TEMPLATE_LIB", None)
    _dbg(
        "B",
        "template patch before",
        {
            "old_STATIC_TEMPLATE_LIB": str(old),
            "fs_templates": str(templates_dir),
            "index_html": index.exists(),
        },
        run_id="post-fix",
    )
    if not index.exists():
        _dbg(
            "B",
            "index.html missing beside gradio package",
            {"templates_dir": str(templates_dir)},
            run_id="post-fix",
        )
        return

    routes.STATIC_TEMPLATE_LIB = str(templates_dir)
    if hasattr(routes, "STATIC_PATH_LIB"):
        routes.STATIC_PATH_LIB = str(templates_dir / "frontend" / "static")
    if hasattr(routes, "BUILD_PATH_LIB"):
        routes.BUILD_PATH_LIB = str(templates_dir / "frontend" / "assets")
    routes.templates = Jinja2Templates(directory=str(templates_dir))
    _dbg(
        "B",
        "template patch after",
        {
            "STATIC_TEMPLATE_LIB": str(routes.STATIC_TEMPLATE_LIB),
            "index_html": True,
        },
        run_id="post-fix",
    )


def _launch_kwargs(port: int) -> dict:
    from gradio.blocks import Blocks

    params = inspect.signature(Blocks.launch).parameters
    kwargs: dict = {
        "server_name": "127.0.0.1",
        "server_port": port,
        "inbrowser": True,
        "show_error": True,
        "quiet": False,
        "share": False,
    }
    if "ssr_mode" in params:
        kwargs["ssr_mode"] = False
    if "show_api" in params:
        kwargs["show_api"] = False
    return kwargs


def _probe_packaged_assets() -> None:
    try:
        import gradio
        import gradio_client
    except Exception as exc:
        _dbg("A", "import gradio failed", {"type": type(exc).__name__, "msg": str(exc)})
        return
    gdir = Path(gradio.__file__).resolve().parent
    cdir = Path(gradio_client.__file__).resolve().parent
    _dbg(
        "A",
        "gradio source files",
        {
            "frozen": bool(getattr(sys, "frozen", False)),
            "gradio_file": str(gradio.__file__),
            "blocks_events_py": (gdir / "blocks_events.py").exists(),
            "blocks_events_pyc": (gdir / "__pycache__" / "blocks_events.cpython-312.pyc").exists()
            or (gdir / "blocks_events.pyc").exists(),
            "component_meta_py": (gdir / "component_meta.py").exists(),
        },
    )
    index = gdir / "templates" / "frontend" / "index.html"
    resources_templates = None
    resources_index = None
    static_lib = None
    try:
        from importlib.resources import files as _files

        resources_templates = str(_files("gradio").joinpath("templates"))
        resources_index = _files("gradio").joinpath("templates", "frontend", "index.html")
        try:
            resources_index_exists = resources_index.is_file()
        except Exception:
            resources_index_exists = False
    except Exception as exc:
        resources_index_exists = f"err:{type(exc).__name__}:{exc}"
    try:
        import gradio.routes as _routes

        static_lib = getattr(_routes, "STATIC_TEMPLATE_LIB", None)
    except Exception:
        static_lib = None
    _dbg(
        "B",
        "gradio frontend templates",
        {
            "templates_dir": (gdir / "templates").exists(),
            "frontend_dir": (gdir / "templates" / "frontend").exists(),
            "index_html": index.exists(),
            "importlib_templates": resources_templates,
            "importlib_index_exists": str(resources_index_exists),
            "STATIC_TEMPLATE_LIB": str(static_lib),
        },
    )
    _dbg(
        "C",
        "gradio_client data files",
        {
            "types_json": (cdir / "types.json").exists(),
            "package_json": (cdir / "package.json").exists(),
        },
    )


def _install_asgi_error_logger() -> None:
    try:
        import gradio.routes as routes
    except Exception as exc:
        _dbg("D", "cannot import gradio.routes", {"type": type(exc).__name__, "msg": str(exc)})
        return
    orig = routes.App.create_app

    @classmethod
    def _create_app_logged(cls, *args, **kwargs):
        app = orig(*args, **kwargs)
        try:
            from starlette.middleware.base import BaseHTTPMiddleware
            from starlette.requests import Request

            class _LogAsgiErrors(BaseHTTPMiddleware):
                async def dispatch(self, request: Request, call_next):
                    try:
                        return await call_next(request)
                    except Exception as err:
                        tb = traceback.format_exc()
                        _dbg(
                            "D",
                            "asgi exception",
                            {
                                "path": request.url.path,
                                "type": type(err).__name__,
                                "msg": str(err)[:800],
                                "tb": tb[-4000:],
                            },
                        )
                        _dbg(
                            "E",
                            "asgi exception class",
                            {"type": type(err).__name__, "module": type(err).__module__},
                        )
                        print("DEBUG FULL TRACEBACK\n" + tb, file=sys.stderr)
                        from starlette.responses import PlainTextResponse

                        return PlainTextResponse(
                            "JhtPoStyles debug traceback\n\n" + tb,
                            status_code=500,
                        )

            app.add_middleware(_LogAsgiErrors)
        except Exception as wrap_exc:
            _dbg(
                "D",
                "failed to wrap asgi",
                {"type": type(wrap_exc).__name__, "msg": str(wrap_exc)},
            )
        return app

    routes.App.create_app = _create_app_logged


def main() -> None:
    # Gradio / analytics / SSR — keep packaging simple (no Node required)
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")
    os.environ.setdefault("GRADIO_SSR_MODE", "False")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    _bypass_proxy_for_localhost()

    _warn_non_ascii_path()

    # Must run before importing playwright-using modules in some packagers
    from jht_po_styles import configure_playwright_browsers_path

    configure_playwright_browsers_path()

    from jht_po_ui import build

    _patch_gradio_localhost_check()
    _probe_packaged_assets()
    _patch_gradio_template_paths()
    _install_asgi_error_logger()

    port = int(os.environ.get("JHT_PO_PORT", _free_port()))
    demo = build()
    demo.launch(**_launch_kwargs(port))


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
