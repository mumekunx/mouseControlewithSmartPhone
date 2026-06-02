# タスク: スマホでPC操作 Webアプリ v1

## 下準備
- [x] aim.md 確定（設計指針）
- [x] feature ブランチ作成
- [x] update.md 立案エントリ

## (A) Python デスクトップアプリ
- [x] app/controller.py — pynput ラッパー（move/click/scroll/down/up/text/key）
- [x] app/server.py — FastAPI 静的配信 + /ws WebSocket + daemon スレッド起動
- [x] app/netinfo.py — LAN IP 取得 + 接続URL + QR画像生成
- [x] app/permissions.py — OS別権限（Mac=アクセシビリティ誘導 / Windows=不要）
- [x] app/window.py — tkinter ウィンドウ（QR・URL・接続状況・権限ボタン）
- [x] app/tray.py — pystray トレイ常駐
- [x] app/main.py — エントリ（権限チェック→サーバー起動→トレイ/窓）
- [x] app/requirements.txt

## (B) Web フロントエンド
- [x] web/index.html — 操作モード + 入力モードの2画面
- [x] web/style.css — 縦持ち固定・拡大防止
- [x] web/app.js — タッチ判定 + WebSocket + IME対応リアルタイム送信

## (C) パッケージング
- [x] packaging/build_mac.spec
- [x] packaging/build_win.spec

## 統合・検証
- [x] Python 構文/起動チェック、ローカルでサーバー起動確認
- [x] サーバー配信・WebSocket・QR・権限ヘルパーの動作確認（venv）
- [x] スマホ実機で接続・カーソル移動を確認 ✅（VPN回避のIP修正＋アクセシビリティ権限付与で成功）
- [ ] 残り操作の確認（左右クリック/スクロール/日本語入力） ← ユーザー環境で
- [ ] GUIウィンドウ版（tkinter）確認 ← `brew install python-tk@3.14` 後
- [ ] PyInstaller で .app / .exe ビルド確認 ← 各OSで
- [x] detail.md 追記
- [x] teach.md 章追加
- [x] README.md 更新
- [x] update.md 進捗・完了マーク

## 次フェーズ（v2 候補）— 2026-06-02 立案
### (1) ドラッグ&ドロップ（クリック長押し）
- [x] `web/app.js`: touchstart 長押し（450ms 静止保持）でドラッグ開始判定 → `down` 送信
- [x] 長押し中の移動は `move`、touchend で `up` 送信（press/release は controller に既存）
- [x] 長押し開始フィードバック（バイブ navigator.vibrate / 視覚変化 `.dragging`）
- [ ] 実機確認（ファイル/選択範囲のドラッグ） ← ユーザー環境で

### (2) DPI / カーソル感度の変更
- [x] `web/index.html`: 感度スライダー（0.5〜3.0）追加
- [x] `web/app.js`: 変更を `{type:"sensitivity", value}` で送信＋localStorage保存
- [x] `app/controller.py`: `SENSITIVITY` を可変化、`sensitivity` type ハンドラ追加（0.1〜5.0クランプ）
- [ ] 実機確認（感度の効き） ← ユーザー環境で

### (3) 入力欄テキストの読み取り→スマホで編集
- [ ] 技術調査: macOS AX API（AXFocusedUIElement→AXValue）/ Windows UI Automation でフォーカス要素のテキスト取得PoC
- [ ] 新規 `app/textfield.py`: OS別の「フォーカス入力欄のテキスト取得」
- [ ] 往復メッセージ: スマホ「編集モード」要求 → `{type:"fieldtext", text}` で返信
- [ ] `web/`: 取得テキストを編集するUI、確定で置換（全選択→削除→type、または差分）
- [ ] 取得失敗時フォールバック（従来の追記入力に戻す）
- [ ] ※難易度高・権限/対応OS課題あり。単独 feature ブランチで進める

## 今後の課題（v1 スコープ外）
- [ ] コード署名・公証（Gatekeeper / SmartScreen 警告の解消）
- [ ] 簡易認証（PIN/トークン）
