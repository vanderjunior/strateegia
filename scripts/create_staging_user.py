#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from app.config import get_app_env, get_studyflow_data_file
from app.repositories.json_store import JsonStudyRepository
from app.services.user_service import LocalUserService


def _read_password() -> str:
    env_password = os.getenv("MENTORIUM_TESTER_PASSWORD")
    if env_password:
        return env_password
    return getpass.getpass("Tester password: ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or confirm a private staging tester user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--email")
    parser.add_argument("--data-file", type=Path, default=get_studyflow_data_file())
    parser.add_argument(
        "--allow-non-staging",
        action="store_true",
        help="Allow local development/test execution. Production still refuses.",
    )
    args = parser.parse_args()

    app_env = get_app_env()
    if app_env == "production":
        raise SystemExit("Refusing to create tester users when APP_ENV=production.")
    if app_env != "staging" and not args.allow_non_staging:
        raise SystemExit("Set APP_ENV=staging or pass --allow-non-staging for local rehearsal.")

    repository = JsonStudyRepository(args.data_file)
    normalized_username = args.username.strip().lower()
    existing = repository.get_user_by_username(normalized_username)
    if existing is not None:
        print(f"User exists: {existing.username}")
        return 0

    user = LocalUserService(repository).register_user(
        username=normalized_username,
        password=_read_password(),
        display_name=args.display_name,
        email=args.email,
    )
    print(f"User created: {user.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
