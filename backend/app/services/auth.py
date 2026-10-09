"""Accounts and sign-in.

Every browser gets a guest learner on first visit, identified by an HttpOnly
cookie holding a random token (the database stores only its SHA-256). A guest
can register a username + password, or link a Google account, to keep their
progress and sign in from other devices. Passwords are hashed with scrypt from
the standard library.
"""
import hashlib
import hmac
import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import AuthSession, User
from .errors import GameError

COOKIE = "duo_session"
USERNAME = re.compile(r"^[a-z0-9_]{3,20}$")


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${key.hex()}"


def check_password(password: str, stored: str | None) -> bool:
    if not stored:
        return False
    _, salt, key = stored.split("$")
    candidate = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(candidate.hex(), key)


def start_session(db: Session, user: User, now: datetime) -> str:
    """Create a sign-in for `user`; returns the raw token for the cookie."""
    token = secrets.token_urlsafe(32)
    db.add(AuthSession(token_hash=_digest(token), user_id=user.id, created_at=now))
    return token


def user_for_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    s = db.get(AuthSession, _digest(token))
    return db.get(User, s.user_id) if s else None


def end_session(db: Session, token: str | None) -> None:
    if token and (s := db.get(AuthSession, _digest(token))):
        db.delete(s)


def register(db: Session, user: User, username: str, password: str) -> None:
    username = username.strip().lower()
    if user.password_hash:
        raise GameError(409, "already_registered", "This account already has a password")
    if not USERNAME.match(username):
        raise GameError(422, "bad_username", "Usernames are 3-20 lowercase letters, digits or _")
    if db.scalar(select(User.id).where(User.username == username, User.id != user.id)):
        raise GameError(409, "username_taken", "That username is taken")
    user.username, user.password_hash = username, hash_password(password)


def login(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username.strip().lower(), User.is_bot.is_(False)))
    if not user or not check_password(password, user.password_hash):
        raise GameError(401, "bad_credentials", "Wrong username or password")
    return user


def verify_google_token(credential: str) -> dict:
    """Check a Google Identity Services ID token and return its claims.
    ponytail: asks Google's tokeninfo endpoint (one HTTP call per sign-in); verify the JWT
    locally against Google's public keys if sign-in volume ever matters."""
    url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"id_token": credential})
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            claims = json.load(r)
    except (urllib.error.URLError, ValueError):
        raise GameError(401, "bad_google_token", "Google sign-in failed, please try again")
    if claims.get("aud") != settings.google_client_id or claims.get("email_verified") not in ("true", True):
        raise GameError(401, "bad_google_token", "Google sign-in failed, please try again")
    return claims


def google_user(db: Session, current: User | None, claims: dict) -> User | None:
    """The learner for this Google account: an existing link, or the current guest
    (who keeps their progress). Returns None if a new account must be created."""
    user = db.scalar(select(User).where(User.google_sub == claims["sub"]))
    if user:
        return user
    if current and not current.password_hash and not current.google_sub:
        current.google_sub, current.email = claims["sub"], claims.get("email")
        if current.display_name == "New learner" and claims.get("name"):
            current.display_name = claims["name"][:60]
        return current
    return None
