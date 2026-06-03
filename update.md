# 進捗ログ（新しいものが上）

## 2026-06-03 16:55 — Codexレビュー追加対応: /info・/qr.png をローカル限定 + touchcancelでドラッグ解除
- **依頼**: 今セッションで Documents側(古い6db38bc)を本番と誤認して重複実装した中から、dev(本番)に未反映の2点だけ取り込む。
  - **(#1)** `/info`・`/qr.png` が LAN 上の誰にでもトークン付き URL/QR を返す＝トークン漏洩で認可バイパス。スマホはこの2つを使わない（QR内token＋index.html/app.jsのみ）ので、両エンドポイントをループバック(127.0.0.1/::1)限定にする。
  - **(#4)** `touchcancel` 未処理で OS のタッチキャンセル時にドラッグ(左押下)が残る → `touchcancel` で `up` 送信＋状態リセット。
- **背景**: dev が本番で大幅に先行。トークン必須化・`compare_digest`・Tailscale非同期(`tailscale_ip_cached`)・疎通確認は既に dev に存在（重複）。未反映は #1/#4 のみ。
- **影響**: `app/server.py`(`_is_local`追加, `info`/`qr_png`をローカル限定), `web/app.js`(touchcancel)。依存追加なし。
- **ブランチ**: `feature/20260603-1655-loopback-touchcancel`（main から分岐）。
- **進捗 — 完了**: server.py に `_is_local()`＋`/info`・`/qr.png` を非ローカル403に、app.js に `touchcancel` ハンドラ追加。検証: py_compile / `node --check` OK。detail.md 更新。**main へのマージはユーザーがPRレビュー後に。実機確認はユーザー環境で**。

## 2026-06-03 13:25 — DPI(感度)上限を3.0→10.0に拡大
- **依頼**: カーソル感度の倍率を最大10倍まで選べるように。
- **方針**: `web/app.js` の感度セレクト生成を 0.5〜10.0 に拡大。0.5〜3.0は0.1刻み(細かい操作用)、3.0〜10.0は0.5刻み(ロールが長くなりすぎないように)。`app/controller.py` のクランプ上限を 5.0→10.0 に。影響2ファイル＋detail.md。
- **ブランチ**: `feature/20260603-1325-dpi-max-10`（pairing-token から分岐）。
- **進捗 (13:2x)**: 実装完了。`web/app.js`（選択肢を0.5〜10.0で生成・低倍率0.1/高倍率0.5刻み）, `app/controller.py`（クランプ 5.0→10.0）, detail.md 更新。検証: node/py_compile OK、選択肢40件(0.5〜10.0・重複なし・3.0/3.5/10.0含む)、クランプ上限10.0確認。実機での効き確認はユーザー環境で。

## 2026-06-03 12:02 — Codexレビュー対応: ペアリング(トークン)必須化・Tailscale検出の非同期化・疎通後ブラウザ起動
- **依頼**: Codex のコードレビューを受けて3点。(1) WS操作にトークン(ペアリング)を必須化、(2) 起動時のTailscale検出をバックグラウンド化、(3) サーバー疎通確認後にブラウザを開く。対象: main.py / server.py / netinfo.py / app.js / host.html。依存追加なし・既存挙動維持。
- **妥当性**: いずれも現状の実弱点に対応＝妥当。現状は無認証で誰でも `/ws` に繋げば操作でき(LAN/Tailscale内とはいえ危険)、起動時に `get_tailscale_ip()` を同期呼び(最大2sブロック)、ブラウザは固定 `sleep(1.0)` で起動(早すぎ/遅すぎ)。
- **方針/影響範囲**:
  - server.py: 起動時に `secrets.token_urlsafe(16)` でトークン生成・保持。`/info`・`/qr.png` の返すURLに `?token=` を付与。`/ws` は accept 後にクエリの token を `secrets.compare_digest` で検証し、不正/欠落なら `close(1008)` で即切断（`handle_message` に到達しない）。/info・/qr.png・host.html 自体（PCローカルの設定用）は従来通り無認証。
  - netinfo.py: `prime_tailscale_ip()`（バックグラウンドで `get_tailscale_ip()` を実行しキャッシュ温め）と `tailscale_ip_cached()`（ブロックしないキャッシュ参照）を追加。
  - main.py: 起動直後に `prime_tailscale_ip()`。ブラウザ起動を「`/info` への GET を `urllib.request` で短いsleep付きリトライ→成功時のみ host.html を開く」方式に変更。トレイの「Tailscale入手」判定は `tailscale_ip_cached()`（非ブロック）に変更。
  - app.js: `location.search` から token を取得し `ws://.../ws?token=` で接続。token 無しは接続せずUIにエラー表示。`close(1008)` 受信時は再接続せずエラー表示。
  - host.html: 接続キーを含むQRである旨の控えめな注意を1行追加（表示URLは自動でtoken付きになる）。
- **ブランチ**: `feature/20260603-1202-pairing-token`（`feature/20260602-1600-live-ime` から分岐＝直前までの作業を含む）。
- **検証方針**: py_compile / node --check。ライブ検証は uvicorn をスレッド起動し urllib+websockets で「token無し/不正のWSは拒否(1008)」「token付き /info・/qr.png が200でURLにtoken付与」「正token WSは accept(操作メッセージは送らずpynput非起動)」を確認。
- **進捗 (12:1x)**: 実装完了。server.py(token生成・`_with_token`・/info・/qr.png・/ws検証), netinfo.py(`prime_tailscale_ip`/`tailscale_ip_cached`), main.py(prime＋疎通確認後ブラウザ起動＋トレイ非ブロック), app.js(token接続・エラーUI), host.html(注意文)。**ライブ検証 全PASS**: /info 200＋url にtoken（Tailscale IPで出た＝prime動作）, /qr.png 200 png, token無し/不正WS→closed 1008, 正token→OPEN維持(pynput非起動)。`_with_token` は `/?token=` でQRリーダー互換。detail.md/todo.md 更新済み。依存追加なし。**実機確認待ち**（QRから操作可・旧QR/直URLは不可・起動が固まらない）。

## 2026-06-02 16:19 — 実機テスト後の改良4件（IME二重入力/濁点バグ修正・感度UI・ピンチズーム）
- **依頼**: iPhone Safari で実機テストした結果の改良点。
  1. 同じ文字が2回連続で入る場合がある（IME二重入力バグ）
  2. て→で の濁点を付けた際に「て」が残る（→「てで」になる）
  3. 感度スライダーが使いにくい。接続中表示の右側に「数字をロールで選ぶ」UIにしたい
  4. 2本指で拡大縮小（ピンチズーム）できるようにしたい
- **原因（①②）**: ライブIME実装が `compositionend` で `kbInput.value=''` クリア＋ compositionイベント差分追跡だったため、(②)濁点で空欄から新規compositionになりPCの旧文字を消せず残る、(①)compositionend と keydown の二重発火で同じ文字を2回送る。
- **対応方針**:
  - ①②: **根本対応**。composition差分追跡をやめ、**入力欄の実値を `input` イベントで前方一致差分ミラー**する単一経路に作り変える。値が同じなら差分ゼロ＝二重送信が原理的に起きない（冪等）。クリアせずバッファ保持、Enterで区切り。特殊キー(Enter/Backspace空時/Tab/Esc)のみ keydown で扱う（`e.isComposing` で変換中は除外）。
  - ③: 感度スライダー(`#sens-slider`)を廃止し、ステータスバー右側に `<select>`(0.5〜3.0)を配置。iOS Safari では select がホイール(ロール)選択になる。localStorage 保存は踏襲。
  - ④: トラックパッド2本指で、指間距離の変化＝ピンチ→ `{type:'zoom', dir:'in'|'out'}`、重心移動＝従来スクロール、を両立。controller は Cmd/Ctrl + `=`/`-`（多くのブラウザ/アプリ共通のズーム）。
- **影響範囲**: `web/app.js`（キーボード作り直し・ピンチ追加・感度をselect化）, `app/controller.py`（zoom追加＋platformでmodキー判定）, `web/index.html`（selectをステータスバーへ移動・スライダー削除・ヒント更新）, `web/style.css`（select配置・sensitivity-row整理）。
- **ブランチ**: `feature/20260602-1600-live-ime`（継続）。
- **進捗 (16:2x)**: 実装完了。`web/app.js`（キーボードをinput実値ミラーに作り直し・ピンチズーム追加・感度をselect化）, `app/controller.py`（zoom追加＋platformでmodキー）, `web/index.html`（selectをステータスバーへ・ヒント更新）, `web/style.css`（.sens-pick追加・旧スライダーCSS削除）。検証: `py_compile`/`node --check` OK、値ミラー差分の単体テスト（濁点て→で/冪等で二重入力なし/変換/削除/中間挿入/絵文字 全PASS）、感度selectの選択肢生成（0.5〜3.0の26件、1.5・3.0含む）OK。detail.md/todo.md 更新済み。**実機再確認待ち**（二重入力解消・濁点・感度ロール・ピンチズーム）。

## 2026-06-02 16:00 — ライブIME入力（変換中の日本語を確定前からPCにリアルタイム反映）
- **依頼**: 機能(3)を再スコープ。当初の「PC側入力欄テキストを読み取って編集」は不要に。代わりに「スマホで日本語を打ちながら、変換確定前のひらがな/変換途中をPCにライブ反映」したい。文章全体の取得・編集はしない。入力だけリアルタイムにPCへ。
- **背景の設計議論**: 既存キーボードは `compositionend`（変換確定）でしか送らず、変換中はPCに何も出ない。これを `compositionupdate` ごとに送ってライブ化する。読み取り編集(AX/クリップボード往復・双方向化)は不要になり、難所が消えてスコープが大幅縮小。
- **方式（ライブIMEミラー / 前方一致差分）**:
  - スマホ側 `web/app.js`: `compositionupdate` ごとに「前回PCに反映済みの文字列」との共通プレフィックスを除いた差分だけを `{type:'compose', back:N, add:"..."}` で送る。コードポイント単位で差分（絵文字対策）。`compositionend` で最終差分を送ってから in-progress 状態をリセット（PC上の確定文字は残す）。
  - PC側 `app/controller.py`: `compose` を受けて `backspace × back → add を type`。状態を持たないステートレス処理。pynput の `type()` は文字を直接挿入するのでPC側IMEを起動せずリテラルに入る（二重変換なし）。
  - **後方互換**: `compositionupdate` を出さない端末でも `compositionend` の最終差分で従来通り確定時に入る＝自動で旧挙動に劣化。
- **影響範囲**: `web/app.js`（compositionハンドラ改修）, `app/controller.py`（compose type追加）の2ファイルのみ。`web/index.html`/`style.css` は変更なし（既存の入力モード画面をそのまま使う）。
- **ブランチ**: `feature/20260602-1600-live-ime`（v2作業は `moreEasy` に f605ddf でコミット済み）。
- **リスク（実機確認必須）**: モバイルIMEの composition イベント挙動は端末差大（iOS Safari / Android Gboard）。大きな変換でのbackspace連打チラつき（前方一致差分で軽減）。PC側欄のオートコンプリート干渉でずれる可能性。
- **進捗 (16:0x)**: 実装完了。`app/controller.py` に `compose` ハンドラ追加、`web/app.js` の composition 処理を差分ライブ送信に改修。検証: `py_compile`/`node --check` OK、差分ロジックの単体テスト（node）で通常変換/end-only劣化/途中削除/キャンセル/絵文字/連続入力の全6ケースPASS。detail.md/teach.md(第9章)/todo.md 更新済み。**実機での日本語ライブ反映はユーザー確認待ち**（[[pynput-gui-cannot-launch-from-claude-bash]] と同様、起動はユーザーのTerminalで）。

## 2026-06-02 05:02 — 次フェーズ機能3件の立案（ドラッグ&ドロップ / 感度・DPI調整 / 入力欄テキスト編集）
- **依頼**: 起動成功後の次TODOとして3機能。(1) クリック長押しでドラッグ&ドロップ、(2) DPI（カーソル感度）を変更できるように、(3) PC側の入力欄の文字を認識→スマホに送って、元の文章を編集できる文字入力。
- **方針/影響範囲**（実装は別ブランチ。ここは立案のみ）:
  - **(1) ドラッグ&ドロップ（長押し）**: 土台は既にある（`controller.py` に `down`=`_mouse.press(left)` / `up`=`_mouse.release(left)`）。主作業は**スマホ側のジェスチャ判定**。`web/app.js` で touchstart から一定時間（例 400〜500ms）指が動かず保持されたら「ドラッグ開始」と判定し `down` 送信→以後の移動は通常の `move`→touchend で `up`。長押し開始時に触覚/視覚フィードバック（バイブ・色変化）を出すと分かりやすい。影響: `web/app.js`（主）, `web/style.css`（任意）。controller側はほぼ変更不要。
  - **(2) DPI / 感度調整**: 現状 `controller.py` の `SENSITIVITY=1.5` 固定。スマホUIにスライダー（例 0.5〜3.0）を追加し、変更を `{type:"sensitivity", value:...}` で送信。`controller.py` にハンドラ追加してグローバル感度を更新（`move` 計算で参照）。永続化したいなら localStorage（スマホ側）で記憶。影響: `web/index.html`（スライダー）, `web/app.js`（送信）, `app/controller.py`（type追加＋可変SENSITIVITY）。
  - **(3) 入力欄テキストの読み取り→スマホで編集**: 最難関。PC側で**現在フォーカスされている入力欄の既存テキストを読む**必要があり、OSのアクセシビリティAPIが要る（macOS=AX API / AXUIElement の AXFocusedUIElement→AXValue、Windows=UI Automation）。pynputでは取得不可。流れ案: スマホで「編集モード」要求→PC側がフォーカス要素のテキストを取得して `{type:"fieldtext", text:...}` で返信→スマホのテキストエリアに表示・編集→確定で「全選択(Cmd/Ctrl+A)→既存削除→新テキストtype」で置換、あるいは差分のみ送る。**要技術調査**（権限・対応OS・取得失敗時フォールバック）。まずは macOS の AX API でフォーカス要素の AXValue 取得PoCから。影響: 新規 `app/textfield.py`（OS別テキスト取得）, `app/server.py`/`controller.py`（往復メッセージ）, `web/`（編集UI）。
- **進捗 (2026-06-02 05:1x)**: **(1)(2) 実装完了**（現 `moreEasy` ブランチ上）。
  - (1) ドラッグ&ドロップ: `web/app.js` に長押し判定（450ms静止保持→`down`、移動でドラッグ、touchend→`up`）、`MOVE_CANCEL_PX`/2本指で解除、バイブ＋`#trackpad.dragging` フィードバック。`web/index.html` ヒント追記、`web/style.css` に `.dragging` 追加。controller側は既存 `down`/`up` 流用で変更なし。
  - (2) 感度/DPI: `web/index.html` にスライダー(0.5〜3.0)、`web/app.js` で `{type:'sensitivity'}` 送信＋localStorage保存＋接続時同期、`app/controller.py` に `sensitivity` ハンドラ（0.1〜5.0クランプ）。`web/style.css` に `.sensitivity-row`。
  - 検証: controller.py py_compile OK、app.js `node --check` OK、感度クランプ単体テストOK（2.5→2.5 / 99→5.0 / 0→0.1 / 不正値→無視）。**実機（長押しドラッグの操作感・感度の効き）はユーザー確認待ち**。detail.md 更新済み。
- **残**: (3) 入力欄テキスト読取→編集 は未着手（要技術調査・単独ブランチ）。

## 2026-06-01 — Tailscale 未検出時のインストール案内（配布相手向け UX）
- **依頼**: 配布相手（特に管理ネットワークで使う人）が迷わないよう、Tailscale が未検出のとき
  「インストールリンク＋手順」をアプリ内に出す。
- **方針/影響範囲**:
  - `web/host.html`: Tailscale 未検出のとき、tailscale.com/download への**クリックできるリンク**と3行手順を表示（検出時は従来の「Tailscale 経由」案内）。
  - `app/tray.py`: `on_get_tailscale` を受け取れるようにし、渡された時だけ「Tailscale を入手」メニューを追加。
  - `app/main.py`: 起動時に `get_tailscale_ip()` を見て、未検出のときだけ「Tailscale を入手」(ダウンロードページを開く)をトレイに追加。
  - 普通の Wi-Fi 利用者には不要なので、あくまで「困ったとき用」の控えめな案内にとどめる。
- **完了**: host.html（未検出時にリンク＋3行手順／検出時は経由案内）、tray.py（`on_get_tailscale` 追加）、main.py（未検出時のみ「Tailscale を入手」メニュー追加）を実装。py_compile OK。実行確認はユーザーのソース起動／再ビルドで。

## 2026-05-31 15:20 — Tailscale 対応（クライアント分離 Wi-Fi の回避）
- **背景**: 実機テストで、現在の Wi-Fi `KUDOS_SECURE_X`(172.19.0.0/16) は**クライアント分離(AP isolation)**が有効（Mac→ルーターは ping 可、Mac→スマホ 172.19.0.81 は 100% 不達で確証）。同一サブネットでも端末間通信が遮断され、スマホからサーバーに届かない。アプリのバグではなくネットワーク仕様。
- **対応**: 独自 NAT 越えは作らず **Tailscale に委譲**。サーバーは全インターフェース待受なので、Tailscale を入れれば 100.x で届く。やったのは「QR/URL が Tailscale IP を案内する」こと。
  - `app/netinfo.py`: `get_tailscale_ip()`(CLI `tailscale ip -4` の複数パス候補→100.64/10 のインターフェース走査、キャッシュ)、`candidate_urls()`(Tailscale→LAN の順)を追加。`build_url()` は主 URL（Tailscale 優先）を返すよう変更。
  - `app/server.py`: `/info` が `candidate_urls` と `tailscale` フラグを返す。
  - `web/host.html`: Tailscale 有効/無効に応じた案内文を表示。
  - 注: バンドル .app は GUI 起動で PATH が最小のため、`_TAILSCALE_BINS` に App Store 版 CLI の絶対パス等を含めて検出。psutil 走査もフォールバックで併用。
- **検証**: py_compile OK。実行確認は環境劣化で不安定なため未→ユーザーが「ソース起動で確認→.app 再ビルド」。
- **ユーザー手順**: 両端末に Tailscale を入れ同一アカウントで ON →（まずソース）`python -m app.main` で QR が 100.x になるか確認 → スマホ(Tailscale ON)で接続 → OK なら `.app` 再ビルド。


## 2026-05-31 01:09 — スマホでPCのマウス/キーボードを操作するWebアプリ v1 実装

### 立案
- **依頼内容**: PC（Mac/Windows）のカーソル移動・クリック・スクロール・文字入力をスマホから行う Web アプリを作る。PC 操作が苦手な人向けに「ターミナル不使用・ダブルクリック起動・QR で接続」を実現する。
- **方針（詳細は aim.md）**:
  - スマホ側 = Web アプリ（縦持ち固定、操作モード＋入力モードの2画面）。
  - PC 側 = Python のデスクトップアプリ（FastAPI/uvicorn サーバーを別スレッド、pynput で制御、pystray でトレイ常駐、tkinter で QR・接続状況・権限案内ウィンドウ）。
  - 通信 = WebSocket（JSON メッセージ）。
  - パッケージ = PyInstaller で .app（Mac）/.exe（Windows）。v1 は未署名。
- **実装体制**: Opus 4.8 がオーケストレーターとなり、サブエージェントで (A) Python デスクトップアプリ、(B) Web フロントエンド を並行実装 → 統合・検証。
- **影響範囲**: 新規 `app/`, `web/`, `packaging/`、ドキュメント `detail.md`/`teach.md`/`tasks/todo.md`/`README.md`。
- **ブランチ**: `feature/20260531-0109-phone-mouse-control`。

### 進捗（2026-05-31 01:30 時点）
- **完了**: `app/`（controller / server / netinfo / permissions / window / tray / main / requirements.txt）、`web/`（index.html / style.css / app.js）、`packaging/`（build_mac.spec / build_win.spec）、`.gitignore` を作成。
- **検証済み（venv で実機確認）**:
  - `python -m py_compile app/*.py` 構文OK、`node --check web/app.js` 構文OK。
  - venv に依存インストール → サーバー起動 → `index.html`/`app.js`/`style.css` 配信OK。
  - `netinfo.build_url`（LAN IP取得）・`make_qr_image`（QR生成）・`permissions.is_trusted()` 動作OK。
  - WebSocket 接続→メッセージ送信で受信ループが落ちないことを確認（接続OPEN維持）。
- **未検証（要・実機）**: GUI（tkinter ウィンドウ＋pystray トレイ）はヘッドレス不可のため、デスクトップで `python -m app.main` 実行時に目視確認が必要。スマホ実機からの一連操作・PyInstaller ビルドも未実施。
- **ドキュメント**: detail.md / teach.md / README.md を実装に合わせて整備。
- **特記事項（ハマりポイント）**: サブエージェントは書き込み許可プロンプトに答えられず（特にバックグラウンド）全滅。`.claude/settings.local.json` の allow はセッション途中で spawn した子には効かなかった。→ オーケストレーター（メイン）が直接実装する方針に切替。

### 2026-05-31 02:10 — 不具合修正: スマホから接続できない（VPNのIPを選んでいた）
- **症状**: ユーザーのターミナルでアプリ起動は成功（サーバーは *:8000 で LISTEN、HTTP 200）したが、スマホから接続できない。
- **原因**: `get_lan_ip()` の「8.8.8.8 へ connect して getsockname」トリックが、VPN(`utun6`, 172.16.0.2)のデフォルト経路 IP を返していた。本物のWi-Fi は `en0`=192.168.10.105。スマホは 172.16.0.2 に届かない。
- **修正**: `netinfo.get_lan_ip()` を psutil ベースに変更し、`utun/tun/ppp/awdl` 等のトンネルを除外して 192.168→10→他 の順で LAN IP を選択。`list_lan_ips()` で候補一覧も返し、ヘッドレス表示で代替 URL も出すように。`requirements.txt` に `psutil` 追加。
- **検証**: 修正後 `get_lan_ip()` → `192.168.10.105`、候補 `['192.168.10.105','172.16.0.2']`（pynput 非依存なので私の環境で確認可）。
- **ユーザー対応**: アプリを再起動すれば QR/URL が 192.168.10.105 になる。即試すなら `http://192.168.10.105:8000` を直接開けば現行サーバーでも届く（全インターフェース待受のため）。

### 完了マーク
- ✅ v1 のコード実装＋サーバー/通信のローカル検証まで完了。LAN IP 検出の VPN 回避も修正済み。実機でカーソル移動も確認済み。

## 2026-05-31 02:40 — ターミナル不要のダブルクリック起動へ設計変更（配布用 .app/.exe）
- **依頼**: ターミナルを使わずに起動したい（他PCにも配れる単独アプリ .app/.exe）。
- **設計変更**: PC側の QR 表示を tkinter ウィンドウから「**起動時に PC のブラウザで QR ページ(/host.html)を自動表示**」に変更。常駐と終了は **pystray メニューバー**で行う。→ tkinter 依存を完全排除（未搭載 Python でも動く・PyInstaller 同梱が楽）。
- **コード変更**:
  - `app/controller.py`: pynput を**遅延 import**（モジュール import 時に Quartz を初期化せず、起動時ハングを回避。サーバー部分を pynput 無しで検証可能に）。
  - `app/server.py`: `/info`(接続URL JSON) と `/qr.png`(QR画像) のルートを追加。
  - `web/host.html`: 新規。PC のブラウザで開く接続案内ページ（QR＋URL＋権限注意）。
  - `app/main.py`: tkinter を廃止し「サーバー起動→ブラウザで /host.html を自動オープン→pystray をメインスレッドで run」に。
  - `app/tray.py`: メニューを「QR を表示／(mac)アクセシビリティ設定／終了」に。
  - `app/window.py`: **削除**（tkinter 不使用）。
  - `packaging/*.spec`: SPECPATH ベースの絶対パスに修正、tkinter 系の hiddenimports を削除、mac は `LSUIElement=True`（メニューバー常駐アプリ）。
- **検証**: 全ファイル py_compile OK。サーバー/エンドポイントの実行確認は環境が劣化して不安定なため未完→ユーザーのビルド・起動で確認。
- **残**: ユーザーが Mac で `pyinstaller packaging/build_mac.spec` を1回実行 → `dist/PhoneMouse.app` をダブルクリック。Windows 版は Windows でビルド。
