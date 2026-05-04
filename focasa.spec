# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

mss_datas, mss_binaries, mss_hiddenimports = collect_all("mss")
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=mss_binaries + pil_binaries,
    datas=mss_datas + pil_datas,
    hiddenimports=mss_hiddenimports
    + pil_hiddenimports
    + [
        "tkinter",
        "tkinter.ttk",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Focasa",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name="Focasa.app",
    icon=None,
    bundle_identifier="xyz.focasa.client",
    info_plist={
        "NSScreenCaptureUsageDescription": "Focasa needs screen recording access to capture screenshots for task tracking.",
        "LSMinimumSystemVersion": "12.0",
    },
)
