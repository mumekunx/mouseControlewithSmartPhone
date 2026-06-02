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

起動すると **PC のブラウザが自動で開き、QR コードと接続 URL** が表示されます。
スマホのカメラで QR を読み取ると、操作画面が開きます。常駐アイコン（メニューバー/タスクトレイ）から
「QR を表示」「終了」ができます（ターミナルを閉じても常駐アイコンから終了可能）。

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

ビルド後は **`dist/PhoneMouse.app`（Mac）/ `dist/PhoneMouse.exe`（Windows）をダブルクリック**するだけ。
起動すると自動でブラウザに QR が出ます（tkinter 不要・メニューバー常駐で終了）。

- v1 は**未署名**です。配布した相手の PC では警告が出ます:
  - macOS: 初回は Finder で「**右クリック → 開く**」で Gatekeeper を回避。
  - Windows: SmartScreen で「**詳細情報 → 実行**」。
- 警告を消すにはコード署名（Apple Developer ID / Windows コード署名証明書）が必要で、今後の課題です。

---

## どの回線でも使う（職場/共用 Wi-Fi・クライアント分離の回避）= Tailscale
`KUDOS_SECURE_X` のような「端末間通信を禁止（AP/クライアント分離）」した Wi-Fi では、同じ LAN にいても
スマホ↔PC が通信できません。これを回避するには **Tailscale**（無料のメッシュ VPN）を使います。

1. **PC（Mac/Windows）に Tailscale を入れてサインイン**（App Store / `brew install --cask tailscale` / tailscale.com）。
2. **スマホにも Tailscale アプリ**を入れ、**同じアカウント**でサインインして **ON**。
3. アプリ（PhoneMouse）を起動 → 表示される QR/URL が **`http://100.x.x.x:8000`（Tailscale の IP）**になります。
4. スマホ（Tailscale ON）でその QR を読む → **回線の種類やクライアント分離に関係なく接続**できます。

> 仕組み: サーバーは全インターフェースで待ち受けているので、Tailscale を入れると 100.x の仮想 IP でも届く。
> アプリは Tailscale の IP を自動検出して QR を出すので、両端末で Tailscale を ON にするだけ。
> Tailscale が無い/OFF のときは従来どおり同じ Wi-Fi 用の LAN IP を案内します。

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
