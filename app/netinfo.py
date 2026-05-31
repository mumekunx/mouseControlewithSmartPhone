"""ネットワーク情報と QR コードを扱うモジュール。

PC の LAN 内 IP アドレスを調べ、スマホがアクセスする URL を組み立て、
その URL の QR コード画像を作る。
"""

import ipaddress
import socket

import qrcode

# VPN / トンネル / 特殊インターフェースの名前の接頭辞。
# これらはスマホから届かないので LAN IP の候補から除外する。
_SKIP_PREFIXES = ("lo", "utun", "tun", "tap", "ppp", "awdl", "llw", "bridge", "gif", "stf")


def _candidates_via_psutil():
    """psutil で「起動中・非トンネル・プライベート」な IPv4 を (名前, IP) で列挙する。"""
    try:
        import psutil
    except Exception:
        return []
    stats = psutil.net_if_stats()
    result = []
    for name, addrs in psutil.net_if_addrs().items():
        st = stats.get(name)
        if st is None or not st.isup:
            continue
        if name.lower().startswith(_SKIP_PREFIXES):
            continue  # VPN/トンネル等は除外
        for a in addrs:
            if a.family == socket.AF_INET and a.address and not a.address.startswith("127."):
                try:
                    if ipaddress.ip_address(a.address).is_private:
                        result.append((name, a.address))
                except ValueError:
                    pass
    return result


def _default_route_ip():
    """デフォルト経路で使われる IP。VPN 接続時は VPN の IP になることがある。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return None
    finally:
        s.close()


def list_lan_ips():
    """スマホからの接続候補となる LAN IPv4 の一覧（重複なし）を返す。"""
    ips = [ip for _, ip in _candidates_via_psutil()]
    d = _default_route_ip()
    if d and d not in ips:
        ips.append(d)
    return ips or ["127.0.0.1"]


def get_lan_ip() -> str:
    """この PC の LAN 内 IP アドレスを返す（VPN/トンネルは避ける）。

    psutil で実インターフェースを調べ、192.168.x → 10.x → その他プライベート の順で
    優先して選ぶ。psutil が無い等のときは、従来のデフォルト経路 IP にフォールバック。
    """
    cands = _candidates_via_psutil()
    if cands:
        def score(item):
            ip = item[1]
            if ip.startswith("192.168."):
                return 0
            if ip.startswith("10."):
                return 1
            return 2
        cands.sort(key=score)
        return cands[0][1]
    return _default_route_ip() or "127.0.0.1"


def build_url(port: int = 8000) -> str:
    """スマホでアクセスする URL（例: http://192.168.0.5:8000）を組み立てる。"""
    return f"http://{get_lan_ip()}:{port}"


def make_qr_image(url: str):
    """URL を QR コード画像(PIL.Image.Image)にして返す。"""
    return qrcode.make(url)


def print_ascii_qr(url: str) -> None:
    """ターミナルに QR コードを文字（ASCII）で表示する。

    GUI が使えないヘッドレスモードで、ターミナルから直接スキャンできるようにする。
    """
    q = qrcode.QRCode(border=1)
    q.add_data(url)
    q.make(fit=True)
    q.print_ascii(invert=True)
