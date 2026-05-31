# mouseControlewithSmartPhone

スマホを PC（Mac / Windows）のトラックパッド＆キーボードにする Web アプリです。
PC で起動 → スマホのカメラで QR を読む → 指でカーソル操作・クリック・スクロール・文字入力ができます。

- スマホ側＝**Web アプリ**（アプリのインストール不要。iOS / Android 両対応）
- PC 側＝**Python のデスクトップアプリ**（ターミナル不要・ダブルクリック起動を目指す）
- 設計の詳細は [aim.md](aim.md)、仕組みの解説は [teach.md](teach.md) を参照。

---

## できること
- カーソル移動（1本指でなぞる）
- 左クリック（タップ）／右クリック（2本指タップ・ボタン）
- スクロール（2本指でなぞる）
- 文字入力（日本語 IME 対応のリアルタイム送信）

---

## 動かし方（開発中・ソースから）

> PC とスマホを**同じ Wi-Fi** につないでおくこと。

```bash
# 1) 依存をインストール（初回のみ）
python3 -m venv .venv
.venv/bin/pip install -r app/requirements.txt   # Windows は .venv\Scripts\pip

# 2) 起動
.venv/bin/python -m app.main                     # Windows は .venv\Scripts\python -m app.main
```

起動するとウィンドウに **QR コード**と接続 URL（例 `http://192.168.0.5:8000`）が出ます。
スマホのカメラで QR を読み取ると、操作画面がブラウザで開きます。

### macOS の権限設定（重要）
マウス／キーを動かすには「アクセシビリティ」の許可が必要です。
- ウィンドウの「権限を設定」ボタン、または
- `システム設定 → プライバシーとセキュリティ → アクセシビリティ`
で、実行しているアプリ（ターミナル / 後述の PhoneMouse.app）を **ON** にしてください。
許可後はアプリを再起動すると確実に反映されます。

### Windows の注意
特別な権限は不要です。初回にファイアウォールの許可ダイアログが出たら「アクセスを許可」を押してください。

---

## 配布用にパッケージ化（ダブルクリック起動）
PyInstaller で実行ファイルを作れます。**OS ごとに、その OS 上で**ビルドしてください（クロスコンパイル不可）。

```bash
.venv/bin/pip install pyinstaller
# macOS
pyinstaller packaging/build_mac.spec      # → dist/PhoneMouse.app
# Windows
pyinstaller packaging/build_win.spec      # → dist/PhoneMouse.exe
```

- v1 は**未署名**です。配布した相手の PC では警告が出ます:
  - macOS: 初回は Finder で「**右クリック → 開く**」で Gatekeeper を回避。
  - Windows: SmartScreen で「**詳細情報 → 実行**」。
- 警告を消すにはコード署名（Apple Developer ID / Windows コード署名証明書）が必要で、今後の課題です。

---

## トラブルシューティング
- **カーソルが動かない（Mac）** → アクセシビリティ権限が未許可。上記設定を確認しアプリ再起動。
- **スマホからつながらない** → 同じ Wi-Fi か確認。ファイアウォールで Python/アプリの受信を許可。
- **QR の URL が `127.0.0.1`** → LAN IP を取得できていない。Wi-Fi 接続を確認。

---

## ディレクトリ構成
```
app/        … PC 側 Python アプリ（controller / server / netinfo / permissions / window / tray / main）
web/        … スマホ側 Web UI（index.html / style.css / app.js）
packaging/  … PyInstaller の spec（Mac / Windows）
aim.md      … 設計方針    teach.md … 仕組み解説    detail.md … ファイル構成    update.md … 進捗ログ
```
