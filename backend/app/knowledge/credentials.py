import json
from dataclasses import dataclass

import keyring


@dataclass(frozen=True)
class SourceCredential:
    username: str
    secret: str


class KnowledgeCredentialStore:
    def __init__(self, service_name: str) -> None:
        self._service_name = f"{service_name}:knowledge-sources"

    def set(self, credential_ref: str, *, username: str, secret: str) -> None:
        keyring.set_password(
            self._service_name,
            credential_ref,
            json.dumps(
                {"username": username, "secret": secret},
                ensure_ascii=False,
            ),
        )

    def get(self, credential_ref: str | None) -> SourceCredential | None:
        if not credential_ref:
            return None
        payload = keyring.get_password(self._service_name, credential_ref)
        if payload is None:
            return None
        parsed = json.loads(payload)
        return SourceCredential(
            username=str(parsed.get("username", "")),
            secret=str(parsed["secret"]),
        )

    def delete(self, credential_ref: str | None) -> None:
        if not credential_ref:
            return
        try:
            keyring.delete_password(self._service_name, credential_ref)
        except keyring.errors.PasswordDeleteError:
            return
