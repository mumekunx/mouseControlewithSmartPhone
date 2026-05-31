# 進捗ログ（新しいものが上）

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
- ✅ v1 のコード実装＋サーバー/通信のローカル検証まで完了。LAN IP 検出の VPN 回避も修正済み。残りは「実機での GUI/操作確認」と「PyInstaller ビルド」（ユーザー環境で実施）。
