import argparse

import keyring

from app.config import Settings
from app.knowledge.security import KnowledgeCipher


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage the Agent Gateway enterprise knowledge key."
    )
    parser.add_argument("command", choices=["init", "status", "delete"])
    args = parser.parse_args()
    settings = Settings()
    service = settings.knowledge_keyring_service
    username = settings.knowledge_keyring_username
    if args.command == "init":
        existing = keyring.get_password(service, username)
        if existing:
            print("Knowledge key already exists.")
            return 0
        keyring.set_password(service, username, KnowledgeCipher.generate_key())
        print("Knowledge key created in the operating system credential store.")
        return 0
    if args.command == "status":
        print("configured" if keyring.get_password(service, username) else "missing")
        return 0
    try:
        keyring.delete_password(service, username)
    except keyring.errors.PasswordDeleteError:
        print("Knowledge key was already absent.")
        return 0
    print("Knowledge key deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
