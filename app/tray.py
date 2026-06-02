"""メニューバー（Mac）/ タスクトレイ（Windows）常駐アイコン。pystray を使う。"""

import platform

import pystray
from PIL import Image, ImageDraw


def _make_icon_image():
    """単色の簡単なアイコン画像を作る（青い丸）。"""
    img = Image.new("RGB", (64, 64), "white")
    d = ImageDraw.Draw(img)
    d.ellipse((12, 12, 52, 52), fill=(74, 108, 247))
    return img


def create_tray(on_open, on_quit, on_permission=None, on_get_tailscale=None):
    """トレイアイコンを作って返す（run() は呼び出し側で行う）。

    on_open:         「QR を表示」で呼ぶ関数（PC のブラウザで接続ページを開く）
    on_quit:         「終了」で呼ぶ関数
    on_permission:   macOS のみ「アクセシビリティ設定を開く」で呼ぶ関数（任意）
    on_get_tailscale: Tailscale 未検出のとき「Tailscale を入手」で呼ぶ関数（任意）
    """
    items = [pystray.MenuItem("QR を表示（接続ページを開く）", lambda icon, item: on_open())]
    if on_get_tailscale:
        items.append(pystray.MenuItem("Tailscale を入手（管理ネットワーク用）", lambda icon, item: on_get_tailscale()))
    if on_permission and platform.system() == "Darwin":
        items.append(pystray.MenuItem("アクセシビリティ設定を開く", lambda icon, item: on_permission()))
    items.append(pystray.MenuItem("終了", lambda icon, item: on_quit()))

    return pystray.Icon("phone_mouse", _make_icon_image(), "スマホでマウス操作", pystray.Menu(*items))
