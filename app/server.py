"""Web ページの配信と WebSocket 通信を担当する FastAPI サーバー。

- "/"          : web/ の静的ファイル（スマホ UI = index.html、PC用ホスト = host.html）
- "/ws"        : スマホからの操作メッセージを受け取る WebSocket
- "/info"      : 接続 URL を JSON で返す（PC のホストページが表示に使う）
- "/qr.png"    : 接続 URL の QR コード画像（PC のホストページが <img> で表示）

受け取ったメッセージは controller.handle_message() に渡してマウス／キーを操作する。
サーバーはバックグラウンドの daemon スレッドで動かし、GUI をブロックしない。
"""

import io
import os
import sys
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import controller, netinfo

# 接続状態が変わったときに呼ぶコールバック（任意）。
_on_status_change = None
_port = 8000


def resource_path(relative: str) -> str:
    """リソース(web/ など)の絶対パスを返す。

    PyInstaller でパッケージ化すると同梱ファイルは sys._MEIPASS 以下に展開される。
    開発中（素のソース実行）はリポジトリのルート基準で解決する。
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, relative)
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, relative)


app = FastAPI()


@app.get("/info")
def info():
    """スマホがアクセスする URL を返す（PC のホストページが表示に使う）。"""
    urls = netinfo.candidate_urls(_port)
    return JSONResponse({"url": urls[0], "urls": urls, "tailscale": netinfo.get_tailscale_ip()})


@app.get("/qr.png")
def qr_png():
    """接続 URL の QR コードを PNG 画像で返す。"""
    img = netinfo.make_qr_image(netinfo.build_url(_port))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


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


# 静的ファイル配信は各ルート定義の後にマウントする（html=True で / が index.html を返す）。
app.mount("/", StaticFiles(directory=resource_path("web"), html=True), name="web")


def start_server_in_thread(port: int = 8000, on_status_change=None):
    """uvicorn サーバーを daemon スレッドで起動し、すぐに return する。"""
    global _on_status_change, _port
    _on_status_change = on_status_change
    _port = port

    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return t
