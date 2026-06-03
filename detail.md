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
  - `SENSITIVITY: float = 1.5` … マウス感度。`sensitivity` メッセージで実行時に変更（0.1〜10.0にクランプ）。
  - `_ensure()` … pynput を**初回操作時に遅延 import** して Controller を用意（import 時の Quartz 初期化＝起動ハングを回避）。
  - `handle_message(msg: dict) -> None` … `type`（move/click/scroll/down/up/text/key/**sensitivity**/**compose**/**zoom**）で分岐。`sensitivity` は感度を更新して即return（pynput不要）。`down`/`up` は左ボタンの押下/解放＝長押しドラッグに使用。`compose` は文字入力のライブ反映用で、`back`回 backspace してから `add` を `type`（前方一致差分。スマホ側が差分を計算して送る＝ここはステートレス）。`zoom` は `_ZOOM_MOD`(mac=Cmd/他=Ctrl) を押しながら `=`(in)/`-`(out)＝拡大縮小。例外は握りつぶす。
- 依存: `pynput`（遅延 import）。
- 被参照: `app/server.py`（受信メッセージを渡す）。

## app/netinfo.py
- 役割: LAN IP の取得（VPN/トンネルを除外）、接続 URL の組み立て、QR コード画像/ASCII の生成。
- 主要:
  - `get_lan_ip() -> str` … psutil で実インターフェースを列挙し、VPN/トンネル(`utun`等)を除外して 192.168→10→他 の順で LAN IP を選ぶ。psutil 無い時は default route IP にフォールバック。
  - `get_tailscale_ip() -> str|None` … Tailscale の自分の IP(100.64.0.0/10)を返す。`tailscale ip -4`(複数パス候補)→ダメなら 100.x のインターフェース走査。結果はキャッシュ。**初回は最大数秒ブロックしうる**ので起動時は直接呼ばない。
  - `tailscale_ip_cached() -> str|None` … キャッシュ値を**ブロックせず**返す（未検出なら None、検出は走らせない）。UI/トレイ判定用。
  - `prime_tailscale_ip() -> None` … `get_tailscale_ip()` を daemon スレッドで走らせてキャッシュを温める（即 return）。起動時に呼ぶ。
  - `candidate_urls(port=8000) -> list[str]` … 接続候補 URL を届きやすい順（Tailscale→LAN）で返す。
  - `list_lan_ips() -> list[str]` … LAN 候補 IP の一覧。
  - `_candidates_via_psutil()` / `_default_route_ip()` … 内部ヘルパー。
  - `build_url(port=8000) -> str` … 主 URL（Tailscale があればそれ、無ければ LAN）= `candidate_urls()[0]`。
  - `make_qr_image(url) -> PIL.Image.Image` … QR 画像。
  - `print_ascii_qr(url) -> None` … ターミナルに QR を文字表示（ヘッドレス用）。
- 依存: `socket`, `ipaddress`, `os`, `shutil`, `subprocess`, `qrcode`(→`pillow`), `psutil`、（任意）`tailscale` CLI。
- 被参照: `app/main.py`, `app/server.py`(`/info`,`/qr.png`)。

## app/server.py
- 役割: FastAPI サーバー。`web/` 配信（`/`）、WebSocket（`/ws`）、接続情報（`/info`）、QR画像（`/qr.png`）を提供し、受信を controller へ渡す。daemon スレッドで起動。**ペアリングトークンで `/ws` 操作を保護**。
- 主要:
  - `app` … FastAPI インスタンス。
  - `_token` … 起動ごとに `secrets.token_urlsafe(16)` で生成するペアリングトークン。`/ws` 操作に必須。
  - `_with_token(url) -> str` … 接続 URL に `/?token=...` を付ける（QRリーダー互換でパス `/` も補う）。
  - `resource_path(relative) -> str` … PyInstaller(`sys._MEIPASS`)対応のパス解決。
  - `info()` … `/info`。**トークン付き**接続 URL を JSON（`url`, `urls`, `tailscale`=`netinfo.tailscale_ip_cached()`）で返す。
  - `qr_png()` … `/qr.png`。**トークン付き**接続 URL の QR を PNG で返す。
  - `ws_endpoint(ws)` … `/ws` ハンドラ。accept 後にクエリの `token` を `secrets.compare_digest` で検証し、不正/欠落なら `close(1008)` で切断（`handle_message` に到達しない）。正なら接続/切断で `_on_status_change` を呼ぶ。
  - `start_server_in_thread(port=8000, on_status_change=None)` … uvicorn を daemon スレッドで起動。
- 依存: `secrets`, `fastapi`, `uvicorn`, `app.controller`, `app.netinfo`。
- 被参照: `app/main.py`。`/info`・`/qr.png`・`host.html`（PCローカルの設定用）は無認証のまま。

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
- 役割: エントリーポイント。サーバー起動(daemon) → Tailscale検出をバックグラウンド開始 → **`/info` の疎通確認(リトライ)が取れてから** PC のブラウザで `/host.html` を自動オープン → pystray をメインスレッドで run（終了まで常駐）。tkinter 不使用。
- 主要: `main()`。`_open_browser_when_ready()`（`urllib.request` で `/info` を最大~5秒リトライし200で開く）、起動時 `netinfo.prime_tailscale_ip()`、トレイの「Tailscale入手」判定は `netinfo.tailscale_ip_cached()`（非ブロック）。トレイ不可時は URL/ASCII QR のヘッドレスにフォールバック。
- 依存: `app.server`, `app.netinfo`, `app.permissions`, `app.tray`, `webbrowser`, `urllib.request`。
- 被参照: 実行起点（`python -m app.main` / PyInstaller のエントリ）。

## app/requirements.txt
- 役割: Python 依存。`fastapi` / `uvicorn[standard]` / `pynput` / `pystray` / `pillow` / `qrcode` / `psutil`。

## web/index.html
- 役割: スマホ UI。2画面（`#screen-control` 操作モード / `#screen-keyboard` 入力モード）。`style.css` と `app.js` を読み込む。
- 主要 id/class: `#trackpad`, `#btn-left`, `#btn-right`, `#btn-open-keyboard`, `#btn-back`, `#kb-input`, `#kb-display`, `#sens-select`(感度セレクト＝ステータスバー右端、JSで選択肢生成), `.sens-pick`, `.status-dot`, `.status-text`, `.screen.active`。
- 依存: `web/style.css`, `web/app.js`。
- 被参照: `app/server.py`（StaticFiles で配信）。

## web/host.html
- 役割: **PC 側**のブラウザで自動的に開く接続案内ページ。大きな QR（`/qr.png`）＋接続 URL（`/info` から取得、**トークン付き**）＋権限注意＋「接続キーを共有しない」注意を表示。スマホはこの QR を読む。
- 依存: サーバーの `/qr.png`, `/info`。
- 被参照: `app/main.py`（起動時に `webbrowser.open`）。

## web/style.css
- 役割: 縦持ち固定・拡大/選択抑止・トラックパッドが残り全領域を占有するレイアウト。`.screen.active` で画面切替、`.status-dot.connected` で接続色、`.sens-pick`(感度セレクトをステータスバー右端に `margin-left:auto` で寄せる)。
- 依存/被参照: `index.html`。

## web/app.js
- 役割: WebSocket クライアント＋トラックパッド判定＋キーボード入力。
- 主要:
  - `connect()` / `send(obj)` / `setConnected(ok)` / `setStatusText(s)` … WS 接続と送信、接続表示更新。`location.search` の `token` を読み `ws://.../ws?token=...` で接続。token 無しは接続せずエラー表示、`close(1008)`(トークン不正)受信時は再接続せずエラー表示。
  - トラックパッド: touchstart/move/end で 1本指=move(rAF間引き) / タップ=click / 2本指=scroll または **ピンチ拡大縮小** / 2本指タップ=右クリック。
  - 長押しドラッグ: 1本指を `LONG_PRESS_MS`(450ms) ほぼ静止保持で `down` 送信＝つかむ→移動でドラッグ→touchend で `up`＝ドロップ。`clearPressTimer()`/`isDragging`/`#trackpad.dragging` で制御。`MOVE_CANCEL_PX` 以上動くか2本指で長押し判定を解除。
  - ピンチズーム: 2本指の指間距離の変化を貯め、`ZOOM_STEP_PX`(28px) ごとに `{type:'zoom', dir:'in'|'out'}` を送る。フレームごとに「距離変化 > 重心移動」ならピンチ(ズーム)、そうでなければスクロールに振り分け（パンとズームを両立）。
  - 感度セレクト: ステータスバー右端の `#sens-select`(0.5〜10.0、0.5〜3.0は0.1刻み/3.0〜10.0は0.5刻みをJS生成)。`change` で `{type:'sensitivity'}` 送信＋localStorage保存、接続時(`sendSensitivity()`)に再同期。iOS Safari ではロール(ホイール)選択になる。
  - キーボード（入力欄の実値をライブミラー）: `kbInput` の**実際の値**を唯一の正とし、`input` イベントごとに `syncFromInput()` が前回反映済み `mirroredCP`（コードポイント配列）との前方一致差分 `{type:'compose', back, add}` を送る。値が同じなら差分ゼロ＝**二重送信が起きない（冪等）**。日本語の変換中・濁点・削除・英数を1経路で処理し、iOSの composition/keydown 二重発火やクリア由来バグを根本回避。特殊キー(Enter/Backspace空時/Tab/Esc)のみ `keydown`(変換中は `e.isComposing` で除外)。Enter/画面切替で `resetMirror()`。
  - `appendDisplay(s)` … 送信内容の確認表示。
- 依存: なし（素の JS）。被参照: `index.html`。

## packaging/build_mac.spec / build_win.spec
- 役割: PyInstaller で `.app`(Mac) / `.exe`(Windows) を生成する設定。`web/` を `datas` で同梱、`hiddenimports` に pynput/pystray/uvicorn の OS 別バックエンド。
- 依存: PyInstaller（ビルド時）。被参照: ビルドコマンドから。

## ドキュメント
- `aim.md` … 設計方針（唯一の正）。`README.md` … 起動/ビルド/権限手順。`teach.md` … 初学者向け解説。`update.md` … 進捗ログ。`tasks/todo.md` … タスク。
