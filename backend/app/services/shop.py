"""Gem shop (gems are mocked — no real payments)."""
from ..clock import Clock
from ..config import settings
from ..models import User
from . import hearts
from .errors import GameError


def _spend(user: User, cost: int) -> None:
    if user.gems < cost:
        raise GameError(402, "not_enough_gems", "You don't have enough gems")
    user.gems -= cost


def refill_hearts(user: User, clock: Clock) -> None:
    hearts.settle_hearts(user, clock.now())
    if user.hearts >= settings.max_hearts:
        raise GameError(409, "hearts_full", "Your hearts are already full")
    _spend(user, settings.heart_refill_gem_cost)
    user.hearts = settings.max_hearts


def buy_streak_freeze(user: User) -> None:
    if user.streak_freezes >= settings.max_streak_freezes:
        raise GameError(409, "freeze_limit", f"You can equip at most {settings.max_streak_freezes} streak freezes")
    _spend(user, settings.streak_freeze_gem_cost)
    user.streak_freezes += 1
