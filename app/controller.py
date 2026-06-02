"""マウス・キーボードを実際に操作するモジュール（pynput ラッパー）。

スマホから届いた JSON メッセージ（dict）に従って PC のマウス／キーボードを動かす。
WebSocket サーバー(server.py)から呼ばれる。

pynput は「最初に操作が来たとき」に遅延 import する。こうすると、
モジュールを import しただけ（サーバー起動だけ）では pynput/Quartz を初期化せず、
GUI セッションでない環境での import ハングを避けられる。
"""

# マウス感度。スマホでの指の移動量(px)に掛けて、カーソルの移動量にする。
SENSITIVITY: float = 1.5

# pynput 関連は初回に遅延ロードする（下記 _ensure 参照）
_mouse = None
_keyboard = None
_Button = None
_Key = None
_KEY_MAP = None


def _ensure():
    """pynput を初回だけ読み込み、Controller と各種定数を用意する。"""
    global _mouse, _keyboard, _Button, _Key, _KEY_MAP
    if _mouse is not None:
        return
    from pynput.mouse import Controller as MouseController, Button
    from pynput.keyboard import Controller as KeyboardController, Key

    _mouse = MouseController()
    _keyboard = KeyboardController()
    _Button = Button
    _Key = Key
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
    global SENSITIVITY
    try:
        _ensure()
        mtype = msg.get("type")

        if mtype == "sensitivity":
            # スマホのスライダーからカーソル感度を変更する。極端な値は安全側にクランプ。
            v = float(msg.get("value", SENSITIVITY))
            SENSITIVITY = max(0.1, min(5.0, v))
            return

        if mtype == "move":
            dx = int(float(msg.get("dx", 0)) * SENSITIVITY)
            dy = int(float(msg.get("dy", 0)) * SENSITIVITY)
            _mouse.move(dx, dy)  # 相対移動

        elif mtype == "click":
            button = _Button.left if msg.get("button") == "left" else _Button.right
            count = 2 if msg.get("double") else 1
            _mouse.click(button, count)

        elif mtype == "scroll":
            _mouse.scroll(float(msg.get("dx", 0)), float(msg.get("dy", 0)))

        elif mtype == "down":
            _mouse.press(_Button.left)

        elif mtype == "up":
            _mouse.release(_Button.left)

        elif mtype == "compose":
            # 変換中（IME composition）のライブ反映。スマホ側が「前回反映済みの文字列」との
            # 前方一致差分を計算し、消す数(back)と足す文字(add)だけ送ってくる。
            # ここでは backspace を back 回 → add を type するだけ（状態を持たないので壊れにくい）。
            back = int(msg.get("back", 0))
            add = str(msg.get("add", ""))
            for _ in range(max(0, back)):
                _keyboard.press(_Key.backspace)
                _keyboard.release(_Key.backspace)
            if add:
                _keyboard.type(add)

        elif mtype == "text":
            _keyboard.type(str(msg.get("text", "")))

        elif mtype == "key":
            k = _KEY_MAP.get(msg.get("key"))
            if k is not None:
                _keyboard.press(k)
                _keyboard.release(k)
        # 未知の type は無視

    except Exception as e:
        print("[controller] メッセージ処理でエラー（無視して継続）:", e)
