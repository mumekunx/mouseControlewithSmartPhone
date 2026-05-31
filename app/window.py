"""接続用の QR コード・接続状況・権限案内を表示する tkinter ウィンドウ。"""

import tkinter as tk

from PIL import ImageTk

from app import permissions


class AppWindow:
    """QR コードと接続状況を表示するメインウィンドウ。"""

    def __init__(self, url, qr_image, on_request_permission=None, on_quit=None):
        self.on_request_permission = on_request_permission
        self.on_quit = on_quit

        self.root = tk.Tk()
        self.root.title("スマホでマウス操作")
        self.root.geometry("360x560")

        # 見出し
        tk.Label(
            self.root,
            text="スマホのカメラでこの QR を読み取ってください",
            wraplength=320,
            font=("", 13),
        ).pack(pady=(16, 8))

        # QR 画像。PhotoImage は参照を保持しないと GC で消えるので self に持つ。
        self._qr_photo = ImageTk.PhotoImage(qr_image.resize((240, 240)))
        tk.Label(self.root, image=self._qr_photo).pack(pady=4)

        # 接続 URL（QR が読めないとき手入力する用）
        tk.Label(self.root, text=url, font=("", 12, "bold")).pack(pady=6)

        # 接続状況
        self._status_var = tk.StringVar(value="● 待機中（スマホの接続待ち）")
        self._status_label = tk.Label(self.root, textvariable=self._status_var, fg="gray")
        self._status_label.pack(pady=6)

        # macOS で権限が無いときだけ「権限を設定」ボタンを出す
        if permissions.needs_permission_ui():
            tk.Label(
                self.root,
                text="⚠ マウス操作には『アクセシビリティ』の許可が必要です",
                fg="red",
                wraplength=320,
            ).pack(pady=(8, 2))
            tk.Button(
                self.root,
                text="権限を設定（システム設定を開く）",
                command=self._request_permission,
            ).pack(pady=4)

        # 閉じる（トレイに格納）／終了
        tk.Button(self.root, text="閉じる（トレイに格納）", command=self.hide).pack(pady=(16, 4))
        tk.Button(self.root, text="終了", command=self._quit).pack(pady=4)

        # ウィンドウの×ボタンは「トレイに格納」にする
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

    def _request_permission(self):
        if self.on_request_permission:
            self.on_request_permission()

    def _quit(self):
        if self.on_quit:
            self.on_quit()
        else:
            self.root.destroy()

    def set_status(self, connected: bool):
        """接続状況を更新する。別スレッド(サーバー)から呼ばれるので root.after で安全に。"""
        text = "● 接続中" if connected else "● 待機中（スマホの接続待ち）"
        color = "green" if connected else "gray"

        def _update():
            self._status_var.set(text)
            self._status_label.config(fg=color)

        try:
            self.root.after(0, _update)
        except Exception:
            pass

    def show(self):
        """ウィンドウを再表示する（トレイの『開く』から呼ばれる）。"""
        self.root.after(0, self.root.deiconify)

    def hide(self):
        """ウィンドウを隠す（トレイに格納）。"""
        self.root.withdraw()

    def run(self):
        """メインスレッドで GUI ループを回す。"""
        self.root.mainloop()
