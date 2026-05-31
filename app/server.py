"""Web ページの配信と WebSocket 通信を担当する FastAPI サーバー。

- "/"   : web/ フォルダの静的ファイル（スマホ UI）を配信
- "/ws" : スマホからの操作メッセージを受け取る WebSocket

受け取ったメッセージは controller.handle_message() に渡してマウス／キーを操作する。
サーバーはバックグラウンドのスレッドで動かし、GUI(ウィンドウ)をブロックしないようにする。
"""

import os
import sys
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app import controller

# 接続状態が変わったときに呼ぶコールバック（GUI の表示更新用）。main.py から渡す。
_on_status_change = None


def resource_path(relative: str) -> str:
    """リソース(web/ など)の絶対パスを返す。

    PyInstaller でパッケージ化すると、同梱ファイルは sys._MEIPASS 以下に展開される。
    開発中（素のソース実行）はリポジトリのルート基準で解決する。
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, relative)
    # app/server.py の2つ上 = リポジトリルート
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, relative)


app = FastAPI()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """スマホからの操作メッセージを受け取り続ける。"""
    await ws.accept()
    if _on_status_change:
        _on_status_change(True)
    try:
        while True:
            data = await ws.receive_json()
            controller.handle_message(data)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("[server] WebSocket エラー:", e)
    finally:
        if _on_status_change:
            _on_status_change(False)


# 静的ファイル配信は /ws を定義した後にマウントする（html=True で / が index.html を返す）。
app.mount("/", StaticFiles(directory=resource_path("web"), html=True), name="web")


def start_server_in_thread(port: int = 8000, on_status_change=None):
    """uvicorn サーバーを daemon スレッドで起動し、すぐに return する。

    daemon スレッドなので、メインスレッド(GUI)が終われば一緒に終了する。
    """
    global _on_status_change
    _on_status_change = on_status_change

    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return t
