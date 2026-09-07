# -*- mode: python ; coding: utf-8 -*-
# Build on Windows only:
#   pyinstaller packaging/jht_po_styles.spec

import sys
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

for pkg in ("gradio", "gradio_client", "safehttpx", "groovy", "playwright"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        hiddenimports += collect_submodules(pkg)
        try:
            datas += collect_data_files(pkg)
        except Exception:
            pass

# Extra Gradio/frontend deps that PyInstaller often misses
for pkg in (
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
    "anyio",
    "httpx",
    "jinja2",
    "multipart",
    "python_multipart",
    "ffmpy",
    "orjson",
    "huggingface_hub",
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [str(project_root / "app_main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
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
    upx=True,
    console=False,  # windowed; Gradio opens the browser
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
    upx=True,
    upx_exclude=[],
    name="JhtPoStyles",
)
