# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_dynamic_libs

mediapipe_binaries = collect_dynamic_libs('mediapipe')


a = Analysis(
    ['game_manager.py'],
    pathex=[],
    binaries=mediapipe_binaries,
    datas=[('image', 'image'), ('pose_image', 'pose_image'), ('sound', 'sound'), ('pose_landmarker_heavy.task', '.'), ('pose_landmarker_full.task', '.'), ('pose_landmarker_lite.task', '.')],
    hiddenimports=['mediapipe.tasks.c'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RACE',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RACE',
)
