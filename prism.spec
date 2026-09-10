# -*- mode: python ; coding: utf-8 -*-
# iValue PRISM — PyInstaller Spec File
# SRS References: §9.7, §8.1.7a, §12.7 STR-10

import os
from PyInstaller.utils.hooks import collect_data_files

# Collect CustomTkinter theme assets & configuration
ctk_datas = collect_data_files('customtkinter')

# Datas to bundle into portable distribution
datas = [
    ('data', 'data'),
    ('themes', 'themes'),
    ('assets', 'assets'),
] + ctk_datas

# Prune non-runtime and heavy test/web frameworks to prevent build hangs and reduce footprint
excludes = [
    'streamlit',
    'altair',
    'pydeck',
    'watchdog',
    'uvicorn',
    'starlette',
    'websockets',
    'pyarrow',
    'tkinter.test',
    'pytest',
    'IPython',
    'jupyter',
    'matplotlib',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'tksheet',
        'PIL',
        'PIL.ImageTk',
        'openpyxl',
        'docx',
        'torch.distributed',
        'unittest',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Native C-bootloader static splash screen (§8.1.7a, STR-10)
splash = Splash(
    'assets/branding/boot_splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
    exclude_binaries=True,
    name='iValue_PRISM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/branding/ivalue_prism.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    splash.binaries,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='iValue_PRISM',
)
