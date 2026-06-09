"""アプリのエントリーポイント（ターミナル不要・ダブルクリック起動向け）。

起動の流れ:
  1) WebSocket サーバーをバックグラウンドの daemon スレッドで起動
  2) PC のブラウザで「接続用 QR ページ(/host.html)」を自動で開く
  3) メニューバー（トレイ）に常駐し、そこから「QR 再表示／権限設定／終了」できる

== 設計メモ ==
QR の表示は tkinter ではなく「PC のブラウザを自動で開く」方式にした。これにより
tkinter 非搭載の Python でも動き、PyInstaller での同梱も楽になる。常駐と終了は
pystray のメニューバーアイコンで行う（pystray はメインスレッドで動かす）。
"""

import os
import sys
import threading
import time
import urllib.request
import webbrowser

# PyInstaller の windowed ビルド（console=False / .app）では sys.stdout/stderr が
# None になり、uvicorn のログ初期化（isatty 参照）や print がクラッシュする。
# None のときは devnull に差し替えて無害化する（Windows/Mac 両対応）。
for _stream_name in ("stdout", "stderr"):
    if getattr(sys, _stream_name) is None:
        setattr(sys, _stream_name, open(os.devnull, "w", encoding="utf-8"))

from app import server, netinfo, permissions, tray


def main():
    # 1) サーバー起動（daemon スレッド）。前回のポートが残っていても
    #    古い自分を終了 → 空きポートへ自動フォールバックし、実際のポートを受け取る。
    port = server.start_server_in_thread(port=8000)
    host_url = f"http://127.0.0.1:{port}/host.html"
    info_url = f"http://127.0.0.1:{port}/info"

    # 1.5) Tailscale 検出はバックグラウンドで（同期で呼ぶと起動が固まるため）
    netinfo.prime_tailscale_ip()

    # 2) サーバーが「応答できる状態」になってから PC のブラウザで QR ページを開く
    def _open_browser_when_ready():
        for _ in range(50):  # 最大 ~5 秒、/info が 200 を返すまで待つ
            try:
                with urllib.request.urlopen(info_url, timeout=0.5) as r:
                    if r.status == 200:
                        break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            print("[main] サーバー疎通が確認できませんでした。手動で開いてください:", host_url)
            return
        try:
            webbrowser.open(host_url)
        except Exception as e:
            print("[main] ブラウザ起動に失敗:", e)

    threading.Thread(target=_open_browser_when_ready, daemon=True).start()

    # 3) メニューバー常駐（メインスレッドで実行）
    try:
        # Tailscale が（今わかっている範囲で）未検出のときだけ「入手」メニューを出す。
        # ブロックしないキャッシュ参照を使う（起動を固まらせない）。
        on_get_tailscale = None
        if not netinfo.tailscale_ip_cached():
            on_get_tailscale = lambda: webbrowser.open("https://tailscale.com/download")

        icon = tray.create_tray(
            on_open=lambda: webbrowser.open(host_url),
            on_quit=lambda: os._exit(0),
            on_permission=permissions.open_accessibility_settings,
            on_get_tailscale=on_get_tailscale,
        )
        icon.run()  # ここでブロック（終了メニューで os._exit）
    except Exception as e:
        # トレイが使えない環境向けフォールバック：URL を表示して待機
        print("[main] メニューバー常駐に失敗。ヘッドレスで継続:", e)
        url = netinfo.build_url(port)
        print("接続 URL:", url)
        try:
            netinfo.print_ascii_qr(url)
        except Exception:
            pass
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n終了します")


if __name__ == "__main__":
    main()
