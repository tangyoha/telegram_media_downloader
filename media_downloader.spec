# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['media_downloader.py'],
    pathex=[],
    binaries=[],
    datas=[('./module/templates','./module/templates'),('./module/static/','./module/static'), ('./module/parsetab.py','./module/'),('./module/parser.out','./module/'),('./config.yaml','./'),('./data.yaml','./')],
    hiddenimports=[],
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
    name='tdl',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='tdl',
)
