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

## 今後の課題（v1 スコープ外）
- [ ] コード署名・公証（Gatekeeper / SmartScreen 警告の解消）
- [ ] 簡易認証（PIN/トークン）
