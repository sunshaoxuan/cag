import argparse

import keyring

from app.config import Settings
from app.knowledge.security import KnowledgeCipher


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage the content-addressed artifact encryption key."
    )
    parser.add_argument("command", choices=["init", "status", "delete"])
    args = parser.parse_args()
    settings = Settings()
    service = settings.artifact_keyring_service
    username = settings.artifact_keyring_username
    if args.command == "init":
        existing = keyring.get_password(service, username)
        if existing:
            print("Artifact key already exists.")
            return 0
        keyring.set_password(service, username, KnowledgeCipher.generate_key())
        print("Artifact key created in the operating system credential store.")
        return 0
    if args.command == "status":
        print("configured" if keyring.get_password(service, username) else "missing")
        return 0
    try:
        keyring.delete_password(service, username)
    except keyring.errors.PasswordDeleteError:
        print("Artifact key was already absent.")
        return 0
    print("Artifact key deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
