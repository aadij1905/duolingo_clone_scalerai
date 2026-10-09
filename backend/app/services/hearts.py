"""Hearts: lose one per wrong answer, regenerate over time.

Regeneration is computed lazily from a timestamp anchor instead of a background
job: whenever we read a learner we "settle" the hearts earned since the anchor.
No cron, no worker, and the result is exact no matter how long the server slept.
"""
from datetime import datetime, timedelta

from ..config import settings
from ..models import User

REGEN = timedelta(minutes=settings.heart_regen_minutes)


def settle_hearts(user: User, now: datetime) -> None:
    if user.hearts >= settings.max_hearts:
        return  # full: nothing to regenerate, and no write on a plain read
    earned = int((now - user.hearts_updated_at) / REGEN)
    if earned <= 0:
        return
    user.hearts = min(settings.max_hearts, user.hearts + earned)
    # Keep the partial progress toward the next heart by advancing the anchor
    # by whole intervals only.
    user.hearts_updated_at += REGEN * earned


def next_heart_at(user: User) -> datetime | None:
    return None if user.hearts >= settings.max_hearts else user.hearts_updated_at + REGEN


def lose_heart(user: User, now: datetime) -> None:
    settle_hearts(user, now)
    if user.hearts >= settings.max_hearts:
        user.hearts_updated_at = now  # regen clock starts at the first loss
    user.hearts = max(0, user.hearts - 1)


def gain_hearts(user: User, n: int, now: datetime) -> None:
    settle_hearts(user, now)
    user.hearts = min(settings.max_hearts, user.hearts + n)
