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
import secrets
import socket
import sys
import threading

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app import controller, netinfo

# /info と /qr.png はトークン付き URL/QR を返すため、PC 自身（ホストページ）以外には
# 渡さない。LAN 上の第三者にトークンを採取されないよう、ループバックからのみ許可する。
_LOOPBACK = {"127.0.0.1", "::1"}


def _is_local(request: Request) -> bool:
    return bool(request.client) and request.client.host in _LOOPBACK

# 接続状態が変わったときに呼ぶコールバック（任意）。
_on_status_change = None
_port = 8000

# 起動ごとに生成するペアリング用トークン。スマホからの操作(/ws)に必須。
# このトークンを含む URL（QR）からつないだ端末だけがマウス/キーを操作できる。
_token = secrets.token_urlsafe(16)


def _with_token(url: str) -> str:
    """接続 URL にトークンを付ける（スマホが ?token=... で開く）。

    netinfo の URL は `http://host:port`（パス無し）なので、QR リーダー互換のため
    `/` を補って `http://host:port/?token=...` の形にする。
    """
    sep = "" if url.endswith("/") else "/"
    return f"{url}{sep}?token={_token}"


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
def info(request: Request):
    """スマホがアクセスする URL（トークン付き）を返す。トークン漏洩防止のためローカル限定。"""
    if not _is_local(request):
        return Response(status_code=403)
    urls = [_with_token(u) for u in netinfo.candidate_urls(_port)]
    return JSONResponse({"url": urls[0], "urls": urls, "tailscale": netinfo.tailscale_ip_cached()})


@app.get("/qr.png")
def qr_png(request: Request):
    """接続 URL（トークン付き）の QR コードを PNG 画像で返す。トークン漏洩防止のためローカル限定。"""
    if not _is_local(request):
        return Response(status_code=403)
    img = netinfo.make_qr_image(_with_token(netinfo.build_url(_port)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    """スマホからの操作メッセージを受け取り続ける。トークンが正しい接続のみ操作可。"""
    await ws.accept()
    # ペアリング検証：正しいトークンが無ければ操作させずに切断（handle_message に到達しない）。
    token = ws.query_params.get("token", "")
    if not token or not secrets.compare_digest(token, _token):
        await ws.close(code=1008)  # 1008 = Policy Violation
        return
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


def _terminate_stale_phonemouse(port: int) -> bool:
    """指定ポートを LISTEN している『PhoneMouse 自身の古いプロセス』だけを終了させる。

    無関係なアプリは絶対に殺さない（プロセス名/コマンドラインで自分の仲間か判定）。
    終了させたら True。psutil が無い/権限不足のときは何もせず False を返す。
    """
    try:
        import psutil
    except Exception:
        return False
    me = os.getpid()
    victims = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] == me:
                continue
            name = (proc.info.get("name") or "").lower()
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            # 開発起動(python -m app.main / app/main.py)とパッケージ版(PhoneMouse)の両対応
            is_ours = (
                "phonemouse" in name
                or "app.main" in cmdline
                or "app/main.py" in cmdline
                or "app\\main.py" in cmdline
            )
            if not is_ours:
                continue
            # そのプロセスが対象ポートを LISTEN しているか
            for c in proc.net_connections(kind="inet"):
                if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port:
                    victims.append(proc)
                    break
        except Exception:
            continue
    if not victims:
        return False
    for p in victims:
        try:
            p.terminate()
        except Exception:
            pass
    gone, alive = psutil.wait_procs(victims, timeout=3)
    for p in alive:  # terminate で死ななければ kill
        try:
            p.kill()
        except Exception:
            pass
    return True


def _find_free_port(preferred: int = 8000, host: str = "0.0.0.0", tries: int = 20) -> int:
    """preferred から順に bind を試し、最初に空いているポートを返す。

    SO_REUSEADDR を付けて TIME_WAIT 残りも再利用可能にする。
    全滅したら preferred を返す（最後は uvicorn 側のエラーに委ねる）。
    """
    for p in range(preferred, preferred + tries):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return preferred


def start_server_in_thread(port: int = 8000, on_status_change=None) -> int:
    """uvicorn サーバーを daemon スレッドで起動し、実際に使うポート番号を返す。

    起動前に、前回残った PhoneMouse 自身を終了させ、空きポートを確保する。
    """
    global _on_status_change, _port
    _on_status_change = on_status_change

    # 前回の自分がポートを握っていたら終了させ、解放を少し待つ
    if _terminate_stale_phonemouse(port):
        import time
        time.sleep(0.3)
    # 基本は元のポート、ダメなら次の空きへ
    port = _find_free_port(port)
    _port = port

    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    return port
