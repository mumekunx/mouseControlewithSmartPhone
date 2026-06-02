# aim.md — 開発指針（スマホで PC のマウス／キーボードを操作する Web アプリ）

> このファイルはプロジェクトの方針書です。ユーザーが自分の見解と異なる部分に修正を加えていきます。
> 修正が入った箇所が「正」です。実装はこのファイルの最新内容に従うこと。

> **設計更新 (2026-05-31)**: ターミナル不要のダブルクリック起動（配布用 .app/.exe）対応に伴い、PC 側の
> QR 表示を **tkinter ウィンドウ → 「起動時に PC のブラウザで QR ページ(/host.html)を自動表示」** に変更。
> 常駐/終了は pystray メニューバーで行い、**tkinter は廃止**（`window.py` 削除）。pynput は遅延 import。
> 詳細は update.md / detail.md 参照。以下の本文中で「tkinter ウィンドウ」と書かれた箇所はこの方式に読み替える。

## 1. 目的（Context）
- PC（Mac / Windows）のカーソル操作・クリック・スクロール・文字入力を、スマホから行えるようにする。
- **PC 操作が苦手な人でも使えること**を最重要視する（ターミナル不使用・ダブルクリック起動・QR で接続）。
- 現状: リポジトリは README のみのグリーンフィールド。実装ゼロ。

## 2. 確定した決定事項（ユーザー確認済み）
| 項目 | 決定 | 理由 |
|------|------|------|
| スマホ側 | **Web アプリ** | アプリインストール不要。同じ Wi-Fi 内で PC にブラウザでアクセス。iOS/Android 両対応。 |
| PC 側言語 | **Python** | pynput（制御）・FastAPI/uvicorn（サーバー）・tkinter（窓）・pystray（トレイ）・qrcode（QR）が Mac/Windows 両対応で、1言語で完結。 |
| 対象 OS（PC側） | **Mac / Windows 両対応** | 配布先を限定しない。Python 製ライブラリ群がいずれも両 OS 対応。 |
| 起動方法 | **ダブルクリックの .app / .exe（ターミナル不使用）** | PC 操作が苦手な人向け。PyInstaller で OS ごとに実行ファイル化。 |
| PC 側 UI | **システムトレイ常駐 ＋ ウィンドウ** | トレイにアイコン常駐（pystray）、クリックでウィンドウ（tkinter）に QR・接続状況・権限ボタンを表示。 |
| 接続方法 | **QR コード** | PC 画面の QR をスマホのカメラで読むだけ。IP の手入力不要。 |
| 機能範囲 | **移動＋クリック＋スクロール＋キーボード入力（フル）** | 実用的なトラックパッドとして使える基本セット。 |

## 3. 完成像
PC で**アプリのアイコンをダブルクリック**して起動 → ウィンドウ（またはトレイ）に表示された **QR コードをスマホのカメラで読む** → スマホのブラウザが開く → 縦持ちで、画面上部の接続状況を確認しつつ、中央の広いトラックパッド領域を操作してカーソル移動・タップでクリック・2本指でスクロール、その下のボタンで左/右クリック。文字入力は「キーボードを開く」ボタンで入力画面に切り替わり、上半分の入力エリア＋下半分のソフトキーボードで打った内容を PC へ送る。

## 4. アーキテクチャ
```
[スマホ ブラウザ]  --WebSocket(JSON)-->  [PC: デスクトップアプリ(Python)]  --pynput-->  [PC のマウス/キーボード]
   トラックパッドUI                       ├ FastAPI/uvicorn サーバー(別スレッド)      (Mac=CGEvent / Windows=SendInput)
                                         ├ トレイ常駐(pystray) + 窓(tkinter)
   (QRをカメラで読んで接続)               └ QR表示・接続状況・権限案内
```
- 1つのデスクトップアプリの中で、①UI 配信＋WebSocket サーバー、②トレイ／ウィンドウ表示、③マウス/キー制御 を行う。
- 同一 LAN 前提。サーバーは `0.0.0.0:8000` で待ち受け、静的ファイル（UI）と WebSocket の両方を提供。サーバーは**バックグラウンドスレッド**で動かし、GUI（tkinter/pystray）はメインスレッドで動かす。
- 連続するカーソル移動は低遅延が要るので HTTP ではなく **WebSocket** を使う。
- ⚠ 実装注意（threading）: macOS では tkinter も pystray も GUI をメインスレッドで動かす必要がある。サーバー（uvicorn）を daemon スレッドに逃がし、GUI をメインに置く構成にする。pystray と tkinter の併用はメインスレッド競合に注意し、必要なら「トレイ常駐を主・ウィンドウは必要時に生成」する形にする。

## 5. ディレクトリ構成（新規作成予定）
```
mouseControlewithSmartPhone/
├── app/
│   ├── main.py            # エントリ: 権限チェック → サーバーを別スレッド起動 → トレイ/窓表示
│   ├── server.py          # FastAPI: 静的配信 + /ws WebSocket（旧 server/main.py 相当）
│   ├── controller.py      # pynput ラッパー: JSONメッセージ -> マウス/キーボード操作
│   ├── tray.py            # pystray トレイ常駐（開く/終了メニュー）
│   ├── window.py          # tkinter ウィンドウ: QRコード・接続URL・接続状況・「権限を設定」ボタン
│   ├── netinfo.py         # LAN IP 取得 + 接続URL組み立て + QR画像生成(qrcode)
│   ├── permissions.py     # OS別の権限チェック/誘導（Mac=アクセシビリティ, Windows=不要）
│   └── requirements.txt   # fastapi, uvicorn[standard], pynput, pystray, pillow, qrcode
├── web/
│   ├── index.html         # 操作モード + 入力モードの2画面
│   ├── app.js             # タッチ処理 + WebSocketクライアント + モード切替
│   └── style.css          # スマホ向けレイアウト（縦持ち固定・拡大防止）
├── packaging/
│   ├── build_mac.spec     # PyInstaller(Mac): .app 生成設定（web/ を同梱）
│   └── build_win.spec     # PyInstaller(Windows): .exe 生成設定（web/ を同梱）
├── aim.md                 # 本ファイル（開発指針）
├── README.md              # 起動手順・権限設定・ビルド手順を追記
├── detail.md              # ファイル構成リファレンス（CLAUDE.md規約）
├── teach.md               # 初学者向け解説（CLAUDE.md規約）
├── update.md              # 進捗ログ（CLAUDE.md規約）
└── tasks/todo.md          # タスク計画（CLAUDE.md規約）
```

## 6. WebSocket メッセージ仕様（JSON）
クライアント → サーバー:
- `{"type":"move","dx":<float>,"dy":<float>}` … 相対移動
- `{"type":"click","button":"left"|"right","double":<bool>}` … クリック
- `{"type":"scroll","dx":<float>,"dy":<float>}` … スクロール（2本指ドラッグ）
- `{"type":"down","button":"left"}` / `{"type":"up","button":"left"}` … ドラッグ（押しっぱなし移動。任意・v1.1）
- `{"type":"text","text":"<文字列>"}` … 文字列をそのまま入力
- `{"type":"key","key":"enter"|"backspace"|"space"|"tab"|"esc"}` … 特殊キー

## 7. 実装内容

### 7.1 server/controller.py（pynput ラッパー）
- `from pynput.mouse import Controller as Mouse, Button` / `from pynput.keyboard import Controller as Keyboard, Key`
- `handle_message(msg: dict)` を1つ用意し、`type` で分岐:
  - move → `mouse.move(dx, dy)`（pynput の `move` は相対移動）。感度係数 `SENSITIVITY`（既定 1.5 程度）を dx,dy に掛ける。
  - click → `mouse.click(Button.left/right, 2 if double else 1)`
  - scroll → `mouse.scroll(dx, dy)`
  - down/up → `mouse.press/release(Button.left)`
  - text → `keyboard.type(text)`
  - key → `Key` enum へマッピング（enter/backspace/space/tab/esc）して `keyboard.press`→`release`
- 不正な type は無視（例外を握りつぶしてサーバーを落とさない）。

### 7.2 app/server.py（FastAPI サーバー）
- `app = FastAPI()`、`web/` を `StaticFiles` でマウント（`/` で index.html を返す）。PyInstaller 同梱時のパス解決に注意（`sys._MEIPASS` 経由でバンドル内 `web/` を参照）。
- `@app.websocket("/ws")`: 受信ループで `await ws.receive_json()` → `controller.handle_message(data)`。切断は try/except で握る。接続/切断時にコールバックで GUI の「接続状況」表示を更新する。
- `start_server_in_thread()`: `uvicorn` をバックグラウンドの daemon スレッドで起動（GUI をブロックしないため）。`host="0.0.0.0", port=8000`。

### 7.4 app/ デスクトップ起動アプリ（ターミナル不使用の肝）
PC 操作が苦手な人向けに、ダブルクリックで起動し画面の指示に従うだけで使えるようにする。

- **app/main.py（エントリ）**: ①`permissions` で権限チェック → ②`server.start_server_in_thread()` でサーバー起動 → ③`tray` でトレイ常駐 ＋ 初回は `window` を表示。GUI をメインスレッドで実行。
- **app/netinfo.py**: `socket` で LAN IP を取得し接続 URL（`http://<IP>:8000`）を組み立て、`qrcode` で QR 画像（PIL Image）を生成して返す。
- **app/window.py（tkinter ウィンドウ）**: 大きめの **QR コード**、接続 URL のテキスト、**接続状況**（接続中/待機中）、**「権限を設定」ボタン**（Mac のみ表示）、「閉じる（トレイに格納）」を表示。
- **app/tray.py（pystray トレイ常駐）**: アイコン常駐。メニュー＝「ウィンドウを開く（QR表示）」「終了」。
- **app/permissions.py（OS 別権限）**:
  - macOS: アクセシビリティ権限の有無をチェックし、無ければ案内＋「設定を開く」で `x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility` を開く。
  - Windows: 特別な権限は不要（何もしない）。初回のファイアウォール許可ダイアログが出たら「許可」する旨を案内に表示。

### 7.3 web/（スマホ UI）
縦持ち固定。**2つの画面（モード）** を切り替えて使う。

#### (A) 操作モード（メイン画面）
上から下へ次の構成。

```
┌───────────────────────────┐
│ ● 接続中                   │  ① 接続状況（ステータスバー・細い）
├───────────────────────────┤
│                           │
│                           │
│        トラックパッド        │  ② トラックパッド（残り全領域を使う・最大）
│   1本指=移動 / 2本指=スクロール  │
│        タップ=左クリック       │
│                           │
│                           │
├───────────────────────────┤
│  [  左クリック  ][  右クリック  ] │  ③ クリック / 右クリック ボタン
├───────────────────────────┤
│  [   ⌨ キーボードを開く   ]   │  ④ 入力モードへ切り替えるボタン
└───────────────────────────┘
```

- **① 接続状況**: 画面最上部の細いバー。WebSocket の接続状態を色付きドット＋テキスト（接続中 / 切断・再接続中）で表示。
- **② トラックパッド**: ①③④を除いた残り全体を占有する最大領域。指の操作（移動・スクロール・タップ）はここで受け付ける。
- **③ クリック / 右クリック**: 横並びの2ボタン。トラックパッド上のタップでもクリックできるが、明示ボタンも用意。
- **④ キーボードを開くボタン**: タップすると下記 (B) 入力モードへ切り替わる。

#### (B) 入力モード（キーボード画面）
④ボタンをタップすると画面が切り替わる。**画面上半分=入力エリア、下半分=スマホのソフトキーボード**。

```
┌───────────────────────────┐
│ ← 戻る            ● 接続中  │  上部バー（操作モードへ戻る）
├───────────────────────────┤
│                           │
│   入力エリア                │  画面上半分。
│   （ここに打った文字が表示・    │  打った内容をそのまま PC へ送信。
│    PC へ送られる）           │
│                           │
├───────────────────────────┤
│   ┌─────────────────────┐  │
│   │  Q W E R T Y U I O P │  │  画面下半分。
│   │   A S D F G H J K L  │  │  スマホ標準のソフトキーボード
│   │  ⇧ Z X C V B N M ⌫  │  │  （input を focus して自動表示）。
│   │   123    [space]  ⏎ │  │
│   └─────────────────────┘  │
└───────────────────────────┘
```

- **上半分（入力エリア）**: focus 状態の入力欄。打った内容を画面でも確認できる。
  - **送信方式 = リアルタイム送信**: 1文字打つごとに即 PC へ送る。印字可能文字は `text`、Backspace/Enter/Space/Tab/Esc は `key` として送信。
  - **日本語 IME の扱い**: 変換中の未確定文字は送らない。`compositionstart` 〜 `compositionend` の間は送信を抑止し、`compositionend`（変換確定）時に確定した文字列を `text` でまとめて送る。英数の直接入力は `keydown`/`input` でそのまま即送信。
  - これにより「ローマ字変換中のゴミ文字が PC に送られる」問題を避ける。
- **下半分（ソフトキーボード）**: スマホ OS 標準のキーボード。入力欄を focus すると自動的にせり上がり、画面下半分を占有する。
- **戻る**: 上部の「← 戻る」で (A) 操作モードへ戻る（ソフトキーボードは閉じる）。
- 実装メモ: (A)/(B) は同一 HTML 内の2つの `<div>`（`screen-control` / `screen-keyboard`）を CSS の表示切替で出し分ける。SPA 的な1ページ内モード切替とし、WebSocket 接続は維持したまま。

#### (C) トラックパッド操作の判定（操作モード内）
- **Touch Events API、`e.touches.length` で指の本数を判定**:
  - 1本指 move → 直前座標との差分 dx,dy を計算して `move` 送信。`requestAnimationFrame` で差分を貯めて1フレーム1送信に間引き。
  - 1本指の短いタップ（移動<10px かつ <200ms）→ `click left`。
  - 2本指タップ → `click right`。
  - 2本指 move → `scroll` 送信。
  - （任意）ダブルタップ後ドラッグ → down/up でドラッグ。
- ③のボタンでも左/右クリックを明示送信できる。

#### (D) 共通の実装メモ
- **WebSocket**: `location.host` から `ws://<host>/ws` に接続。切断時は自動再接続（数秒間隔）。接続状態を①に表示。
- **モバイル最適化**: `viewport user-scalable=no`、`touch-action: none`、長押しメニュー無効化で既定ジェスチャ干渉を防ぐ。
- デスクトップでの確認は Chrome DevTools のモバイルエミュレーション（タッチエミュレート）で行う。

## 8. ドキュメント運用（CLAUDE.md 規約）
- `tasks/todo.md`: タスクをチェックリスト化。
- `update.md`: 「立案」を先に追記 → 作業ごとに進捗追記 → 完了マーク。
- `detail.md`: 新規ファイルの役割・主要関数・依存・被参照を記載。
- `teach.md`: 初学者向けに「WebSocket とは」「相対座標でのカーソル移動」「pynput とアクセシビリティ権限」「タッチイベントの差分計算」を解説。
- `README.md`: 起動手順・権限設定・接続方法を追記。

## 9. ブランチ運用（CLAUDE.md 規約）
- 実装は新規ブランチで: `feature/<date +%Y%m%d-%H%M>-phone-mouse-control`。
- main に直接コミットしない。merge/push はユーザーが PR レビュー後に実施。

## 10. OS 別の権限（重要・ハマりポイント）
- **macOS（アクセシビリティ権限が必要）**:
  - pynput でマウス／キーボードを動かすには「システム設定 → プライバシーとセキュリティ → アクセシビリティ」で許可が必要。未許可だとカーソルが動かない。
  - **.app にパッケージ化すると権限の付与先がアプリ自身**（例「マウス操作.app」）になり分かりやすい。一度許可すれば次回以降そのまま使える。
  - アプリ起動時に `permissions.py` で権限有無を判定 → 無ければウィンドウに案内＋「権限を設定」ボタンで設定画面を直接開く。
- **Windows（特別な権限は不要）**:
  - pynput はそのままマウス／キー操作できる。初回にファイアウォールの許可ダイアログが出たら「アクセスを許可する」を押す旨を案内に表示。

## 10b. 配布・ビルド（PyInstaller、OS ごとに別ビルド）
- PyInstaller は**クロスコンパイル不可**。`.app` は Mac で、`.exe` は Windows でビルドする（同一ソース）。`web/` を同梱する設定にする。
- **コード署名（配布時の警告回避・コストあり）**:
  - macOS: 未署名だと Gatekeeper 警告。回避には Apple Developer ID 署名＋公証（有料・年$99）。**v1 は未署名＋「右クリック→開く」の回避手順を案内**。
  - Windows: 未署名だと SmartScreen 警告。回避にはコード署名証明書（有料）。**v1 は未署名＋「詳細情報→実行」の回避手順を案内**。
  - → 署名・公証は後続の課題。まず動くものを優先する。

## 11. セキュリティ注意
- LAN 内の誰でも接続すると相手の PC を操作できてしまう。v1 は同一 Wi-Fi 前提のシンプル構成とし、リスクを README に明記。
- 任意の強化案（後続）: 起動時に PIN を表示し、WS 接続時にトークン照合する簡易認証。

## 12. 動作確認（検証手順）
### 開発中（ソースから）
1. `pip install -r app/requirements.txt`（or 仮想環境）。
2. `python -m app.main` で起動 → トレイ常駐＋ウィンドウに QR と接続 URL が出る。
3. macOS は初回アクセシビリティ権限を付与しアプリを再起動。Windows はファイアウォール許可。
4. **デスクトップ確認**: PC ブラウザで `http://localhost:8000`、DevTools モバイルエミュレーションでトラックパッド操作 → カーソル移動／タップでクリック／テキスト入力（IME含む）／2本指スクロールを確認。
5. **実機確認**: スマホで PC 画面の QR を読む → 開いたページで移動・クリック・右クリック・スクロール・キーボード入力（日本語変換含む）を一通り確認。
6. WebSocket 切断 → 自動再接続を確認。接続状況表示が連動するか確認。

### パッケージ後（配布物）
7. PyInstaller で `.app`（Mac）/`.exe`（Windows）をビルドし、**ダブルクリックだけ**で 2〜6 が成立するか各 OS で確認（ターミナルを一切使わない経路）。

## 13. スコープ外（今回はやらない）
- インターネット越し（NAT 越え）操作、HTTPS/TLS。※ただし **Tailscale 対応は追加済み**（2026-05-31）。
  クライアント分離された Wi-Fi でも、両端末に Tailscale を入れれば 100.x 経由で接続可能。アプリは Tailscale IP を
  自動検出し QR を出す（`netinfo.get_tailscale_ip`/`candidate_urls`）。独自の NAT 越え実装はしない（Tailscale に委譲）。
- スマホ側のネイティブアプリ化（iOS / Android）。※スマホ側は特定 OS に限定せず、Web アプリで iOS・Android 両対応とする。
- PC 側 Linux 対応（当面は Mac / Windows のみ）。
- コード署名・公証（v1 は未署名＋警告回避手順の案内で対応。署名は後続課題）。
- 複数 PC への接続切り替え。
- スクロール以外の高度なマルチタッチジェスチャ（ピンチ等）。
