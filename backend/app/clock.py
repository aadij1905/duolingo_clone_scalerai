"""Injectable clock.

All "what time / what day is it" questions go through this object so that
streak and heart-regeneration logic can be tested deterministically and the
hosted demo can "time travel" (POST /api/dev/time-travel) without touching the
system clock. Each learner travels alone: their offset is stored on their row.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from .db import get_db


class Clock:
    def __init__(self, offset: timedelta = timedelta()) -> None:
        self.offset = offset

    def now(self) -> datetime:
        """Current UTC time (naive, as stored in SQLite) plus any simulated offset."""
        return datetime.now(timezone.utc).replace(tzinfo=None) + self.offset

    def today(self, tz: str = "UTC") -> date:
        """The learner's local calendar date; streaks are counted in local days."""
        try:
            zone = ZoneInfo(tz)
        except Exception:  # unknown tz string from the client -> fall back to UTC
            zone = timezone.utc
        return self.now().replace(tzinfo=timezone.utc).astimezone(zone).date()

    def travel(self, days: float) -> None:
        self.offset += timedelta(days=days)

    def reset(self) -> None:
        self.offset = timedelta()


clock = Clock()  # plain server time: seeding and startup


def get_clock(db: Session = Depends(get_db), duo_session: str | None = Cookie(None)) -> Clock:
    """FastAPI dependency: server time plus this learner's time-travel offset.
    Tests override it with their own Clock."""
    from .services.auth import user_for_token  # late import: services import this module's types
    user = user_for_token(db, duo_session)
    return Clock(timedelta(seconds=user.clock_offset_s) if user else timedelta())
