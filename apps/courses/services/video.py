"""Legacy PHP AES-256-CBC (double base64) video URL decryption + YouTube embed normalisation."""
import base64
import re

from django.conf import settings

_PLAIN_PREFIXES = ("http://", "https://", "//", "www.", "youtube.com", "youtu.be")


def decrypt_video_url(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    value = str(encrypted_value).strip()
    if value.startswith(_PLAIN_PREFIXES):
        return value
    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        raw = base64.b64decode(base64.b64decode(value))
        key = settings.AES_KEY.encode().ljust(32, b"\x00")[:32]
        iv = settings.AES_IV.encode()[:16]
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend()).decryptor()
        data = decryptor.update(raw) + decryptor.finalize()
        pad = data[-1]
        if 1 <= pad <= 16:
            data = data[:-pad]
        return data.decode("utf-8", errors="ignore") or value
    except Exception:
        return value


def to_embed_url(url: str) -> str:
    if not url or "youtube.com/embed/" in url:
        return url or ""
    for pattern in (r"youtu\.be/([\w-]+)", r"[?&]v=([\w-]+)", r"youtube\.com/(?:live|shorts)/([\w-]+)"):
        match = re.search(pattern, url)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
    return url
