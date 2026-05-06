# PyInstaller one-folder build (faster cold start than --onefile).
# Run from pos-system:  pyinstaller smartstock.spec
#
# UPX must stay off: compressing Python DLLs / stdlib often causes
# "Failed to import encodings module" at EXE startup on Windows.

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = Path(SPECPATH).resolve()
_icon = root / "assets" / "smartstock.ico"
_exe_icon = str(_icon) if _icon.is_file() else None
_migration_datas = [
    (str(p), "app/database/migrations")
    for p in sorted((root / "app" / "database" / "migrations").glob("m*.py"))
]
_legacy_migration = root / "app" / "database" / "migrations.py"
if _legacy_migration.is_file():
    _migration_datas.append((str(_legacy_migration), "app/database"))

a = Analysis(
    [str(root / "run.py")],
    pathex=[str(root)],
    binaries=[],
    datas=_migration_datas,
    hiddenimports=list(collect_submodules("encodings"))
    + list(collect_submodules("app.database.migrations")),
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
    name="SmartStock",
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
    icon=_exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="V01",
)
