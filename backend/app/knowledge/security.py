import base64
import hashlib
import re
from dataclasses import dataclass
from os import urandom

import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import Settings


SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{20,}\b"),
    re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key)\s*[:=]\s*[\"']?[^\s\"']{8,}"
    ),
    re.compile(
        r"(?im)^[^\r\n]*(?:パスワード|暗証番号|秘密鍵|認証キー)"
        r"[^\r\n]*$"
    ),
    re.compile(
        r"(?im)^\s*(?:ユーザー(?:名)?|ユーザ(?:名)?|アカウント(?:名)?|"
        r"ログイン(?:名)?|接続先|ホスト(?:名)?|IP(?:アドレス)?|"
        r"endpoint|host(?:name)?|user(?:name)?)\s*[:：=\t]"
        r"[^\r\n]*$"
    ),
    re.compile(
        r"(?i)\b(?:https?|ssh|svn)://[^\s/:]+:[^\s/@]+@[^\s]+"
    ),
)
PROMPT_INJECTION_PATTERNS = (
    re.compile(r"(?i)ignore (?:all |the )?(?:previous|prior) instructions"),
    re.compile(r"(?i)system prompt"),
    re.compile(r"(?i)developer message"),
)


@dataclass(frozen=True)
class ScanResult:
    safe_text: str
    secret_detected: bool
    prompt_injection_detected: bool


class KnowledgeCipher:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("Knowledge encryption key must be 32 bytes")
        self._cipher = AESGCM(key)

    def encrypt(self, text: str) -> str:
        nonce = urandom(12)
        encrypted = self._cipher.encrypt(nonce, text.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")

    def decrypt(self, value: str) -> str:
        payload = base64.urlsafe_b64decode(value.encode("ascii"))
        return self._cipher.decrypt(payload[:12], payload[12:], None).decode("utf-8")

    @staticmethod
    def generate_key() -> str:
        return base64.urlsafe_b64encode(urandom(32)).decode("ascii")


def load_knowledge_cipher(settings: Settings) -> KnowledgeCipher | None:
    encoded_key = settings.knowledge_encryption_key
    if not encoded_key:
        try:
            encoded_key = keyring.get_password(
                settings.knowledge_keyring_service,
                settings.knowledge_keyring_username,
            )
        except Exception:
            encoded_key = None
    if not encoded_key:
        return None
    try:
        key = base64.urlsafe_b64decode(encoded_key.encode("ascii"))
    except ValueError:
        key = hashlib.sha256(encoded_key.encode("utf-8")).digest()
    return KnowledgeCipher(key)


def scan_knowledge_text(text: str) -> ScanResult:
    secret_detected = any(pattern.search(text) for pattern in SECRET_PATTERNS)
    injection_detected = any(
        pattern.search(text) for pattern in PROMPT_INJECTION_PATTERNS
    )
    safe_text = text
    for pattern in SECRET_PATTERNS:
        safe_text = pattern.sub("[REDACTED_SECRET]", safe_text)
    return ScanResult(
        safe_text=safe_text,
        secret_detected=secret_detected,
        prompt_injection_detected=injection_detected,
    )
