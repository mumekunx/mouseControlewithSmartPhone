# PyInstaller spec — macOS .app ビルド用
#
# ビルド: リポジトリルートで  pyinstaller packaging/build_mac.spec
# 注意:
#   - PyInstaller はクロスコンパイル不可。Mac の .app は Mac でビルドすること。
#   - v1 は未署名。初回起動は Finder で「右クリック → 開く」で Gatekeeper を回避する。
#   - hiddenimports は不足が出たらビルドエラーを見て追記する。
#   - SPECPATH は PyInstaller がこの spec のあるディレクトリ(packaging/)を入れてくれる。
import os

repo_root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(repo_root, "app", "main.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[(os.path.join(repo_root, "web"), "web")],  # スマホ UI / ホストページを同梱
    hiddenimports=[
        "pynput.mouse._darwin", "pynput.keyboard._darwin",
        "pystray._darwin",
        "uvicorn.logging", "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="PhoneMouse", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="PhoneMouse")
app = BUNDLE(
    coll,
    name="PhoneMouse.app",
    icon=None,
    bundle_identifier="com.example.phonemouse",
    # メニューバー常駐アプリにする（Dock アイコンや必須ウィンドウ無しで動く）
    info_plist={"LSUIElement": True},
)
