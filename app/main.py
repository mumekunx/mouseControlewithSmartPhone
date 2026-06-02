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
import threading
import time
import webbrowser

from app import server, netinfo, permissions, tray


def main():
    port = 8000
    host_url = f"http://127.0.0.1:{port}/host.html"

    # 1) サーバー起動（daemon スレッド）
    server.start_server_in_thread(port=port)

    # 2) サーバーが立ち上がってから PC のブラウザで QR ページを開く
    def _open_browser():
        time.sleep(1.0)
        try:
            webbrowser.open(host_url)
        except Exception as e:
            print("[main] ブラウザ起動に失敗:", e)

    threading.Thread(target=_open_browser, daemon=True).start()

    # 3) メニューバー常駐（メインスレッドで実行）
    try:
        # Tailscale が未検出のときだけ「入手」メニューを出す（管理ネットワーク向けの案内）
        on_get_tailscale = None
        if not netinfo.get_tailscale_ip():
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
