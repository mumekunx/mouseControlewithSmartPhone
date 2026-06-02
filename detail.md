# detail.md — ファイル構成リファレンス

「何があるか」のリファレンス。各ファイルの役割・主要な型/関数・依存・被参照を記載する。
（なぜ/どう動くかの解説は teach.md、進捗は update.md、設計方針は aim.md）

---

## app/__init__.py
- 役割: `app` を Python パッケージにするマーカー。
- 主要: なし（コメントのみ）。
- 依存: なし / 被参照: パッケージ全体。

## app/controller.py
- 役割: スマホから来た JSON メッセージに従って、実際に PC のマウス／キーボードを操作する（pynput ラッパー）。
- 主要:
  - `SENSITIVITY: float = 1.5` … マウス感度。`sensitivity` メッセージで実行時に変更（0.1〜5.0にクランプ）。
  - `_ensure()` … pynput を**初回操作時に遅延 import** して Controller を用意（import 時の Quartz 初期化＝起動ハングを回避）。
  - `handle_message(msg: dict) -> None` … `type`（move/click/scroll/down/up/text/key/**sensitivity**）で分岐。`sensitivity` は感度を更新して即return（pynput不要）。`down`/`up` は左ボタンの押下/解放＝長押しドラッグに使用。例外は握りつぶす。
- 依存: `pynput`（遅延 import）。
- 被参照: `app/server.py`（受信メッセージを渡す）。

## app/netinfo.py
- 役割: LAN IP の取得（VPN/トンネルを除外）、接続 URL の組み立て、QR コード画像/ASCII の生成。
- 主要:
  - `get_lan_ip() -> str` … psutil で実インターフェースを列挙し、VPN/トンネル(`utun`等)を除外して 192.168→10→他 の順で LAN IP を選ぶ。psutil 無い時は default route IP にフォールバック。
  - `get_tailscale_ip() -> str|None` … Tailscale の自分の IP(100.64.0.0/10)を返す。`tailscale ip -4`(複数パス候補)→ダメなら 100.x のインターフェース走査。結果はキャッシュ。クライアント分離や別回線でも通信したい時に使う。
  - `candidate_urls(port=8000) -> list[str]` … 接続候補 URL を届きやすい順（Tailscale→LAN）で返す。
  - `list_lan_ips() -> list[str]` … LAN 候補 IP の一覧。
  - `_candidates_via_psutil()` / `_default_route_ip()` … 内部ヘルパー。
  - `build_url(port=8000) -> str` … 主 URL（Tailscale があればそれ、無ければ LAN）= `candidate_urls()[0]`。
  - `make_qr_image(url) -> PIL.Image.Image` … QR 画像。
  - `print_ascii_qr(url) -> None` … ターミナルに QR を文字表示（ヘッドレス用）。
- 依存: `socket`, `ipaddress`, `os`, `shutil`, `subprocess`, `qrcode`(→`pillow`), `psutil`、（任意）`tailscale` CLI。
- 被参照: `app/main.py`, `app/server.py`(`/info`,`/qr.png`)。

## app/server.py
- 役割: FastAPI サーバー。`web/` 配信（`/`）、WebSocket（`/ws`）、接続情報（`/info`）、QR画像（`/qr.png`）を提供し、受信を controller へ渡す。daemon スレッドで起動。
- 主要:
  - `app` … FastAPI インスタンス。
  - `resource_path(relative) -> str` … PyInstaller(`sys._MEIPASS`)対応のパス解決。
  - `info()` … `/info`。接続 URL を JSON（`url`, `urls`）で返す（PC のホストページ用）。
  - `qr_png()` … `/qr.png`。接続 URL の QR を PNG で返す。
  - `ws_endpoint(ws)` … `/ws` ハンドラ。接続/切断で `_on_status_change` を呼ぶ。
  - `start_server_in_thread(port=8000, on_status_change=None)` … uvicorn を daemon スレッドで起動。
- 依存: `fastapi`, `uvicorn`, `app.controller`, `app.netinfo`。
- 被参照: `app/main.py`。

## app/permissions.py
- 役割: OS 別の権限判定（macOS=アクセシビリティ / Windows=不要）。
- 主要:
  - `is_trusted() -> bool` … macOS は `AXIsProcessTrusted()`、他 OS は常に True。
  - `needs_permission_ui() -> bool` … macOS かつ未許可で True。
  - `open_accessibility_settings() -> None` … macOS のアクセシビリティ設定を開く。
- 依存: `platform`, `subprocess`、（macOS 実行時のみ）pyobjc 系（pynput が連れてくる）。
- 被参照: `app/window.py`, `app/main.py`。

## app/tray.py
- 役割: メニューバー（Mac）/ タスクトレイ（Windows）常駐アイコン。終了・QR再表示の入口。
- 主要:
  - `_make_icon_image()` … PIL でアイコン画像生成。
  - `create_tray(on_open, on_quit, on_permission=None, on_get_tailscale=None) -> pystray.Icon` … メニュー「QR を表示／(任意)Tailscale を入手／(mac)アクセシビリティ設定／終了」。
- 依存: `pystray`, `PIL`, `platform`。
- 被参照: `app/main.py`。
- 備考: 旧 `app/window.py`(tkinter ウィンドウ) は廃止・削除。QR 表示は PC のブラウザ(`/host.html`)に移行。

## app/main.py
- 役割: エントリーポイント。サーバー起動(daemon) → PC のブラウザで `/host.html` を自動オープン → pystray をメインスレッドで run（終了まで常駐）。tkinter 不使用。
- 主要: `main()`。トレイ不可時は URL/ASCII QR 表示のヘッドレスにフォールバック。
- 依存: `app.server`, `app.netinfo`, `app.permissions`, `app.tray`, `webbrowser`。
- 被参照: 実行起点（`python -m app.main` / PyInstaller のエントリ）。

## app/requirements.txt
- 役割: Python 依存。`fastapi` / `uvicorn[standard]` / `pynput` / `pystray` / `pillow` / `qrcode` / `psutil`。

## web/index.html
- 役割: スマホ UI。2画面（`#screen-control` 操作モード / `#screen-keyboard` 入力モード）。`style.css` と `app.js` を読み込む。
- 主要 id/class: `#trackpad`, `#btn-left`, `#btn-right`, `#btn-open-keyboard`, `#btn-back`, `#kb-input`, `#kb-display`, `#sens-slider`/`#sens-value`(感度スライダー), `.sensitivity-row`, `.status-dot`, `.status-text`, `.screen.active`。
- 依存: `web/style.css`, `web/app.js`。
- 被参照: `app/server.py`（StaticFiles で配信）。

## web/host.html
- 役割: **PC 側**のブラウザで自動的に開く接続案内ページ。大きな QR（`/qr.png`）＋接続 URL（`/info` から取得）＋権限注意を表示。スマホはこの QR を読む。
- 依存: サーバーの `/qr.png`, `/info`。
- 被参照: `app/main.py`（起動時に `webbrowser.open`）。

## web/style.css
- 役割: 縦持ち固定・拡大/選択抑止・トラックパッドが残り全領域を占有するレイアウト。`.screen.active` で画面切替、`.status-dot.connected` で接続色。
- 依存/被参照: `index.html`。

## web/app.js
- 役割: WebSocket クライアント＋トラックパッド判定＋キーボード入力。
- 主要:
  - `connect()` / `send(obj)` / `setConnected(ok)` … WS 接続（自動再接続）と送信、接続表示更新。
  - トラックパッド: touchstart/move/end で 1本指=move(rAF間引き) / タップ=click / 2本指=scroll・右クリック。
  - 長押しドラッグ: 1本指を `LONG_PRESS_MS`(450ms) ほぼ静止保持で `down` 送信＝つかむ→移動でドラッグ→touchend で `up`＝ドロップ。`clearPressTimer()`/`isDragging`/`#trackpad.dragging` で制御。`MOVE_CANCEL_PX` 以上動くか2本指で長押し判定を解除。
  - 感度スライダー: `#sens-slider`(0.5〜3.0) を `input` で `{type:'sensitivity'}` 送信＋localStorage保存、接続時(`sendSensitivity()`)に再同期。
  - キーボード: `compositionstart`/`compositionend`(IME確定送信)、`keydown`(英数即送信・特殊キー)。
  - `appendDisplay(s)` … 送信内容の確認表示。
- 依存: なし（素の JS）。被参照: `index.html`。

## packaging/build_mac.spec / build_win.spec
- 役割: PyInstaller で `.app`(Mac) / `.exe`(Windows) を生成する設定。`web/` を `datas` で同梱、`hiddenimports` に pynput/pystray/uvicorn の OS 別バックエンド。
- 依存: PyInstaller（ビルド時）。被参照: ビルドコマンドから。

## ドキュメント
- `aim.md` … 設計方針（唯一の正）。`README.md` … 起動/ビルド/権限手順。`teach.md` … 初学者向け解説。`update.md` … 進捗ログ。`tasks/todo.md` … タスク。
