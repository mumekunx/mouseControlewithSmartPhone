"""システムトレイ（Mac のメニューバー / Windows のタスクトレイ）常駐アイコン。"""

import pystray
from PIL import Image, ImageDraw


def _make_icon_image():
    """単色の簡単なアイコン画像を作る（青い丸）。"""
    img = Image.new("RGB", (64, 64), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((12, 12, 52, 52), fill=(74, 108, 247))
    return img


def create_tray(on_open, on_quit):
    """トレイアイコンを作って返す（run() は呼び出し側で行う）。

    on_open: メニュー「ウィンドウを開く」で呼ぶ関数
    on_quit: メニュー「終了」で呼ぶ関数
    """
    menu = pystray.Menu(
        pystray.MenuItem("ウィンドウを開く", lambda icon, item: on_open()),
        pystray.MenuItem("終了", lambda icon, item: on_quit()),
    )
    return pystray.Icon("phone_mouse", _make_icon_image(), "スマホでマウス操作", menu)
