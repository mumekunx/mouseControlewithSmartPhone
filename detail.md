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
  - `SENSITIVITY: float = 1.5` … マウス感度。
  - `handle_message(msg: dict) -> None` … `type`（move/click/scroll/down/up/text/key）で分岐。例外は握りつぶす。
  - `_mouse` / `_keyboard` … pynput の Controller（モジュールレベル）。
  - `_KEY_MAP` … 特殊キー名 → pynput `Key` のマッピング。
- 依存: `pynput`。
- 被参照: `app/server.py`（受信メッセージを渡す）。

## app/netinfo.py
- 役割: LAN IP の取得（VPN/トンネルを除外）、接続 URL の組み立て、QR コード画像/ASCII の生成。
- 主要:
  - `get_lan_ip() -> str` … psutil で実インターフェースを列挙し、VPN/トンネル(`utun`等)を除外して 192.168→10→他 の順で LAN IP を選ぶ。psutil 無い時は default route IP にフォールバック。
  - `list_lan_ips() -> list[str]` … 接続候補 IP の一覧（つながらない時の代替表示用）。
  - `_candidates_via_psutil()` / `_default_route_ip()` … 内部ヘルパー。
  - `build_url(port=8000) -> str` … `http://<IP>:<port>`。
  - `make_qr_image(url) -> PIL.Image.Image` … QR 画像。
  - `print_ascii_qr(url) -> None` … ターミナルに QR を文字表示（ヘッドレス用）。
- 依存: `socket`, `ipaddress`, `qrcode`(→`pillow`), `psutil`。
- 被参照: `app/main.py`。

## app/server.py
- 役割: FastAPI サーバー。`web/` 配信（`/`）と WebSocket（`/ws`）を提供し、受信を controller へ渡す。daemon スレッドで起動。
- 主要:
  - `app` … FastAPI インスタンス。
  - `resource_path(relative) -> str` … PyInstaller(`sys._MEIPASS`)対応のパス解決。
  - `ws_endpoint(ws)` … `/ws` ハンドラ。接続/切断で `_on_status_change` を呼ぶ。
  - `start_server_in_thread(port=8000, on_status_change=None)` … uvicorn を daemon スレッドで起動。
- 依存: `fastapi`, `uvicorn`, `app.controller`。
- 被参照: `app/main.py`。

## app/permissions.py
- 役割: OS 別の権限判定（macOS=アクセシビリティ / Windows=不要）。
- 主要:
  - `is_trusted() -> bool` … macOS は `AXIsProcessTrusted()`、他 OS は常に True。
  - `needs_permission_ui() -> bool` … macOS かつ未許可で True。
  - `open_accessibility_settings() -> None` … macOS のアクセシビリティ設定を開く。
- 依存: `platform`, `subprocess`、（macOS 実行時のみ）pyobjc 系（pynput が連れてくる）。
- 被参照: `app/window.py`, `app/main.py`。

## app/window.py
- 役割: QR コード・接続 URL・接続状況・権限ボタンを表示する tkinter ウィンドウ。
- 主要:
  - `class AppWindow` … `__init__(url, qr_image, on_request_permission, on_quit)`、`set_status(connected)`、`show()`、`hide()`、`run()`。
- 依存: `tkinter`, `PIL.ImageTk`, `app.permissions`。
- 被参照: `app/main.py`。

## app/tray.py
- 役割: システムトレイ（メニューバー/タスクトレイ）常駐アイコン。
- 主要:
  - `_make_icon_image()` … PIL でアイコン画像生成。
  - `create_tray(on_open, on_quit) -> pystray.Icon` … メニュー「ウィンドウを開く」「終了」。
- 依存: `pystray`, `PIL`。
- 被参照: `app/main.py`。

## app/main.py
- 役割: エントリーポイント。URL/QR 準備 → ウィンドウ作成 → サーバー起動(別スレッド) → トレイ起動(別スレッド) → GUI メインループ。
- 主要: `main()`。スレッド方針をコメントで明記（サーバー=daemon、tkinter=メイン、pystray=別スレッドのベストエフォート）。
- 依存: `app.server`, `app.netinfo`, `app.permissions`, `app.window`, `app.tray`。
- 被参照: 実行起点（`python -m app.main` / PyInstaller のエントリ）。

## app/requirements.txt
- 役割: Python 依存。`fastapi` / `uvicorn[standard]` / `pynput` / `pystray` / `pillow` / `qrcode` / `psutil`。

## web/index.html
- 役割: スマホ UI。2画面（`#screen-control` 操作モード / `#screen-keyboard` 入力モード）。`style.css` と `app.js` を読み込む。
- 主要 id/class: `#trackpad`, `#btn-left`, `#btn-right`, `#btn-open-keyboard`, `#btn-back`, `#kb-input`, `#kb-display`, `.status-dot`, `.status-text`, `.screen.active`。
- 依存: `web/style.css`, `web/app.js`。
- 被参照: `app/server.py`（StaticFiles で配信）。

## web/style.css
- 役割: 縦持ち固定・拡大/選択抑止・トラックパッドが残り全領域を占有するレイアウト。`.screen.active` で画面切替、`.status-dot.connected` で接続色。
- 依存/被参照: `index.html`。

## web/app.js
- 役割: WebSocket クライアント＋トラックパッド判定＋キーボード入力。
- 主要:
  - `connect()` / `send(obj)` / `setConnected(ok)` … WS 接続（自動再接続）と送信、接続表示更新。
  - トラックパッド: touchstart/move/end で 1本指=move(rAF間引き) / タップ=click / 2本指=scroll・右クリック。
  - キーボード: `compositionstart`/`compositionend`(IME確定送信)、`keydown`(英数即送信・特殊キー)。
  - `appendDisplay(s)` … 送信内容の確認表示。
- 依存: なし（素の JS）。被参照: `index.html`。

## packaging/build_mac.spec / build_win.spec
- 役割: PyInstaller で `.app`(Mac) / `.exe`(Windows) を生成する設定。`web/` を `datas` で同梱、`hiddenimports` に pynput/pystray/uvicorn の OS 別バックエンド。
- 依存: PyInstaller（ビルド時）。被参照: ビルドコマンドから。

## ドキュメント
- `aim.md` … 設計方針（唯一の正）。`README.md` … 起動/ビルド/権限手順。`teach.md` … 初学者向け解説。`update.md` … 進捗ログ。`tasks/todo.md` … タスク。
