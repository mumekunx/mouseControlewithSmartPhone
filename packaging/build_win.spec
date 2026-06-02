# PyInstaller spec — Windows .exe ビルド用
#
# ビルド: リポジトリルートで  pyinstaller packaging/build_win.spec
# 注意:
#   - PyInstaller はクロスコンパイル不可。Windows の .exe は Windows でビルドすること。
#   - onefile 構成（1つの .exe にまとめる。配布が楽）。
#   - v1 は未署名。初回起動は SmartScreen で「詳細情報 → 実行」で回避する。
#   - hiddenimports は不足が出たらビルドエラーを見て追記する。
import os

repo_root = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(repo_root, "app", "main.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[(os.path.join(repo_root, "web"), "web")],  # スマホ UI / ホストページを同梱
    hiddenimports=[
        "pynput.mouse._win32", "pynput.keyboard._win32",
        "pystray._win32",
        "uvicorn.logging", "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
# onefile: a.binaries と a.datas を EXE に含め、COLLECT を使わない
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="PhoneMouse", console=False)
