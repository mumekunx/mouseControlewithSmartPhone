# PyInstaller spec — macOS .app ビルド用
#
# ビルド: リポジトリルートで  pyinstaller packaging/build_mac.spec
# 注意:
#   - PyInstaller はクロスコンパイル不可。Mac の .app は Mac でビルドすること。
#   - v1 は未署名。初回起動は Finder で「右クリック → 開く」で Gatekeeper を回避する。
#   - hiddenimports は不足が出たらビルドエラーを見て追記する。
import os

repo_root = os.path.abspath(os.getcwd())

a = Analysis(
    ['../app/main.py'],
    pathex=[repo_root],
    binaries=[],
    datas=[('../web', 'web')],  # スマホ UI を同梱（server.resource_path が参照）
    hiddenimports=[
        'pynput.mouse._darwin', 'pynput.keyboard._darwin',
        'pystray._darwin',
        'PIL.ImageTk',
        'uvicorn.logging', 'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PhoneMouse', console=False)
coll = COLLECT(exe, a.binaries, a.datas, name='PhoneMouse')
app = BUNDLE(coll, name='PhoneMouse.app', icon=None,
             bundle_identifier='com.example.phonemouse')
