"""Request-scoped dependencies (dependency inversion: routers ask for a User and a
Clock; how they're produced lives here)."""
from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from .clock import Clock, get_clock
from .db import get_db
from .models import User
from .services import auth, hearts, leaderboard, streak
from .services.errors import GameError


def current_user(db: Session = Depends(get_db), clock: Clock = Depends(get_clock),
                 duo_session: str | None = Cookie(None)) -> User:
    """The signed-in learner (cookie set by POST /api/auth/guest, /login or /register).

    Lazily settles time-based state (heart regen, missed streak days, league
    promotion) so every endpoint sees an up-to-date learner without any background job.
    """
    user = auth.user_for_token(db, duo_session)
    if not user:
        raise GameError(401, "unauthenticated", "Sign in or start as a guest")
    hearts.settle_hearts(user, clock.now())
    user.streak_event = streak.settle_streak(user, clock.today(user.timezone))  # transient, for the UI
    user.league_event = leaderboard.settle_league(db, user, clock.now())
    if db.dirty:
        db.commit()
    return user
