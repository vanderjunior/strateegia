from __future__ import annotations

import hashlib
import hmac
import secrets
from uuid import uuid4

from app.domain.models import User, utc_now
from app.repositories.json_store import JsonStudyRepository


class LocalUserService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def register_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        email: str | None = None,
    ) -> User:
        normalized_username = username.strip().lower()
        if not normalized_username:
            raise ValueError("Username is required.")
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        user = User(
            user_id=str(uuid4()),
            username=normalized_username,
            email=email.strip().lower() if email else None,
            display_name=display_name.strip() or normalized_username,
            password_hash=self.hash_password(password),
            created_at=utc_now(),
            is_active=True,
        )
        return self.repository.create_user(user)

    def authenticate(self, *, username: str, password: str) -> User | None:
        user = self.repository.get_user_by_username(username.strip().lower())
        if user is None or not user.is_active:
            return None
        if not self.verify_password(password, user.password_hash):
            return None
        user.last_login_at = utc_now()
        self.repository.update_user(user)
        return user

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        iterations = 200_000
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return f"pbkdf2_sha256${iterations}${salt}${derived}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            algorithm, raw_iterations, salt, expected = stored_hash.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(raw_iterations),
        ).hex()
        return hmac.compare_digest(derived, expected)
