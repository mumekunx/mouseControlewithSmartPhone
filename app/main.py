"""アプリのエントリーポイント。

起動の流れ:
  1) 接続 URL と QR 画像を用意
  2) GUI(tkinter ウィンドウ + pystray トレイ)が使えれば GUI モードで起動
     使えなければ「ヘッドレスモード」に自動フォールバック（URL と QR をターミナル表示）
  3) WebSocket サーバーはバックグラウンドの daemon スレッドで起動

== スレッドの方針（重要）==
tkinter も pystray も「GUI はメインスレッドで動かす」のが前提。両方を同時に
ネイティブのループで回すのは難しいので、本アプリは:
  - uvicorn サーバー → daemon スレッド
  - tkinter ウィンドウ → メインスレッド（mainloop）
  - pystray トレイ → 別スレッドでベストエフォート起動
とする。

== ヘッドレスフォールバック ==
tkinter が入っていない Python や、GUI セッションの無い環境では、ウィンドウを
作らずにサーバーだけ起動し、接続 URL と QR をターミナルに出す。これにより
GUI が無くてもスマホからの接続・操作テストができる。
"""

import os
import time

from app import server, netinfo, permissions


def _run_gui(url, qr):
    """GUI モード。ウィンドウ生成に失敗したら False を返す（呼び出し側で headless へ）。"""
    try:
        from app import window, tray  # ここで tkinter / pystray を import
    except Exception as e:
        print("[main] GUI(tkinter/pystray)が利用できません:", e)
        return False

    try:
        win = window.AppWindow(
            url=url,
            qr_image=qr,
            on_request_permission=permissions.open_accessibility_settings,
            on_quit=lambda: os._exit(0),
        )
    except Exception as e:
        # tkinter はあるが画面(ウィンドウサーバー)に繋げない等
        print("[main] ウィンドウ生成に失敗:", e)
        return False

    # サーバー起動（接続/切断をウィンドウ表示へ反映）
    server.start_server_in_thread(port=8000, on_status_change=win.set_status)

    # トレイ常駐（ベストエフォート）
    try:
        import threading
        icon = tray.create_tray(on_open=win.show, on_quit=lambda: os._exit(0))
        threading.Thread(target=icon.run, daemon=True).start()
    except Exception as e:
        print("[main] トレイの起動に失敗（ウィンドウのみで継続）:", e)

    win.run()  # メインスレッドで GUI ループ
    return True


def _run_headless(url, qr):
    """GUI が使えない環境向け。サーバーを起動し、URL と QR をターミナルに表示する。"""
    server.start_server_in_thread(port=8000)

    # QR を画像ファイルにも保存しておく（ターミナルが読めない場合の保険）
    qr_note = ""
    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = os.path.join(repo_root, "connect_qr.png")
        qr.save(out)
        qr_note = f"QR画像も保存しました: {out}"
    except Exception as e:
        qr_note = f"QR画像の保存に失敗: {e}"

    print("=" * 56)
    print(" スマホ（同じ Wi-Fi）でこの URL を開いてください:")
    print("    " + url)
    # 候補が複数あるとき（VPN 等）は、つながらない場合の代替も表示する
    others = [ip for ip in netinfo.list_lan_ips() if f"http://{ip}:8000" != url]
    if others:
        print(" つながらない場合は、こちらも試してください:")
        for ip in others:
            print(f"    http://{ip}:8000")
    print("=" * 56)
    try:
        netinfo.print_ascii_qr(url)  # ターミナルから直接スキャンできる QR
    except Exception as e:
        print("(QRのターミナル表示に失敗:", e, ")")
    print(qr_note)
    if permissions.needs_permission_ui():
        print("⚠ macOS: マウス操作にはアクセシビリティ権限の許可が必要です")
    print("終了するには Ctrl+C")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n終了します")


def main():
    port = 8000
    url = netinfo.build_url(port)
    qr = netinfo.make_qr_image(url)

    # まず GUI を試し、ダメならヘッドレスへ
    if not _run_gui(url, qr):
        _run_headless(url, qr)


if __name__ == "__main__":
    main()
