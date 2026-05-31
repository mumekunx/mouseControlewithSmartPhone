"""OS 別の権限判定ユーティリティ。

macOS ではアクセシビリティ権限が無いと pynput でマウス/キーが動かないため、
起動時に権限の有無を判定して案内 UI を出すために使う。
Windows やその他 OS では特別な権限は不要なので常に許可済みとして扱う。
"""

import platform
import subprocess


def is_trusted() -> bool:
    """アクセシビリティ権限を持っているか（操作可能か）を返す。

    - Windows / その他 OS: 権限不要なので常に True。
    - macOS (Darwin): AXIsProcessTrusted() の結果を返す。
      PyObjC が無い／判定不能のときは安全側に倒して False（未許可扱い）。
    """
    if platform.system() != "Darwin":
        return True

    # macOS: PyObjC 経由でアクセシビリティ権限を確認する。
    for module_name in ("ApplicationServices", "Quartz", "HIServices"):
        try:
            mod = __import__(module_name, fromlist=["AXIsProcessTrusted"])
            return bool(mod.AXIsProcessTrusted())
        except Exception:
            continue

    # 判定不能 → 未許可扱い（安全側）
    return False


def needs_permission_ui() -> bool:
    """権限案内 UI を表示すべきか。macOS かつ未許可のときだけ True。"""
    return platform.system() == "Darwin" and not is_trusted()


def open_accessibility_settings() -> None:
    """macOS のアクセシビリティ設定画面を直接開く。他 OS では何もしない。"""
    if platform.system() == "Darwin":
        subprocess.run(
            [
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
            ]
        )
