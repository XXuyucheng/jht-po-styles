# -*- mode: python ; coding: utf-8 -*-
# Build on Windows only:
#   pyinstaller packaging/jht_po_styles.spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None
project_root = Path(SPECPATH).resolve().parent

datas = []
binaries = []
hiddenimports = [
    "jht_po_styles",
    "jht_po_ui",
    "playwright",
    "playwright.sync_api",
    "gradio",
]

# collect_all is required for Gradio (templates/frontend) and Playwright (driver).
# Also pull FastAPI stack as real packages — hiddenimports alone often still miss data files.
for pkg in (
    "gradio",
    "gradio_client",
    "safehttpx",
    "groovy",
    "playwright",
    "fastapi",
    "starlette",
    "uvicorn",
    "httpx",
    "anyio",
    "jinja2",
    "pydantic",
    "pydantic_core",
    "python_multipart",
    "multipart",
    "aiofiles",
    "ffmpy",
    "orjson",
    "huggingface_hub",
    "markupsafe",
    "yaml",
    "greenlet",
    "httpcore",
    "h11",
    "sniffio",
    "idna",
    "certifi",
    "websockets",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        try:
            hiddenimports += collect_submodules(pkg)
        except Exception:
            pass
        try:
            datas += collect_data_files(pkg)
        except Exception:
            pass

# Explicit Gradio frontend (Jinja looks up frontend/index.html at GET /).
try:
    import gradio as _gradio_pkg

    _gradio_templates = Path(_gradio_pkg.__file__).resolve().parent / "templates"
    if _gradio_templates.exists():
        datas.append((str(_gradio_templates), "gradio/templates"))
except Exception:
    pass

a = Analysis(
    [str(project_root / "app_main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(project_root / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    # Gradio inspects its own .py files when serving the page.
    # Without this, GET / returns Internal Server Error (missing blocks_events.py).
    module_collection_mode={
        "gradio": "py",
        "gradio_client": "py",
        "groovy": "py",
    },
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JhtPoStyles",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX often breaks DLLs / trips antivirus on Windows
    console=True,  # show Gradio URL + startup errors in a console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "packaging" / "icon.ico")
    if (project_root / "packaging" / "icon.ico").exists()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="JhtPoStyles",
)
