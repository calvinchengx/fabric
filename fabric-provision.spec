# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the fabric-provision CLI (single-folder bundle).
# Build from repo root: uv sync --group packaging && uv run pyinstaller fabric-provision.spec
# Run: ./dist/fabric-provision/fabric-provision --help
#
# PyInstaller is not a cross-compiler: build on each target OS (Windows / Linux / macOS) you ship.
# https://pyinstaller.org/

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

spec_dir = Path(SPECPATH)
repo_root = spec_dir
src_path = str(repo_root / "src")
entry = str(repo_root / "src/fabric_provisioner/cli.py")

block_cipher = None

# Pull metadata + data files for stacks that introspect at runtime (hooks cover rich/typer).
_datas = []
_binaries = []
_hidden = []
for pkg in ("pydantic", "httpx", "certifi"):
    d, b, h = collect_all(pkg)
    _datas += d
    _binaries += b
    _hidden += h

a = Analysis(
    [entry],
    pathex=[src_path],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hidden
    + [
        "fabric_provisioner",
        "fabric_provisioner.api",
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="fabric-provision",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="fabric-provision",
)
