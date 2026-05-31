"""マウス・キーボードを実際に操作するモジュール（pynput ラッパー）。

スマホから届いた JSON メッセージ（dict）を受け取り、その内容に応じて
PC のマウス／キーボードを動かす。WebSocket サーバー(server.py)から呼ばれる。
"""

from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

# マウス感度。スマホでの指の移動量(px)に掛けて、カーソルの移動量にする。
# 大きくすると少しの指の動きで大きくカーソルが動く。
SENSITIVITY: float = 1.5

# Controller はプロセスで1つ作れば良いので、モジュールレベルで生成する。
_mouse = MouseController()
_keyboard = KeyboardController()

# 特殊キー名（スマホから来る文字列）→ pynput の Key へのマッピング
_KEY_MAP = {
    "enter": Key.enter,
    "backspace": Key.backspace,
    "space": Key.space,
    "tab": Key.tab,
    "esc": Key.esc,
}


def handle_message(msg: dict) -> None:
    """1件のメッセージを処理して、マウス／キーボードを操作する。

    どんな入力が来てもサーバーを落とさないよう、例外は握りつぶして警告のみ出す。
    """
    try:
        mtype = msg.get("type")

        if mtype == "move":
            # 相対移動（現在位置からの差分だけ動かす）
            dx = int(float(msg.get("dx", 0)) * SENSITIVITY)
            dy = int(float(msg.get("dy", 0)) * SENSITIVITY)
            _mouse.move(dx, dy)

        elif mtype == "click":
            button = Button.left if msg.get("button") == "left" else Button.right
            count = 2 if msg.get("double") else 1
            _mouse.click(button, count)

        elif mtype == "scroll":
            _mouse.scroll(float(msg.get("dx", 0)), float(msg.get("dy", 0)))

        elif mtype == "down":
            _mouse.press(Button.left)

        elif mtype == "up":
            _mouse.release(Button.left)

        elif mtype == "text":
            _keyboard.type(str(msg.get("text", "")))

        elif mtype == "key":
            k = _KEY_MAP.get(msg.get("key"))
            if k is not None:
                _keyboard.press(k)
                _keyboard.release(k)
        # 未知の type は何もしない（無視）

    except Exception as e:
        # 1件のエラーでサーバー全体を止めない
        print("[controller] メッセージ処理でエラー（無視して継続）:", e)
