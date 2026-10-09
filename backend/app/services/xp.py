"""XP ledger: every award is an XpEvent row; User.xp_total is a denormalised sum."""
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import User, XpEvent


def award_xp(db: Session, user: User, amount: int, source: str, today: date, now: datetime,
             session_id: str | None = None) -> None:
    db.add(XpEvent(user_id=user.id, session_id=session_id, amount=amount, source=source,
                   local_date=today, created_at=now))
    user.xp_total += amount


def xp_on(db: Session, user_id: int, day: date) -> int:
    return db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0))
                     .where(XpEvent.user_id == user_id, XpEvent.local_date == day))


def xp_last_days(db: Session, user_id: int, today: date, days: int = 7) -> list[dict]:
    """XP per day for the profile chart, oldest first, zero-filled."""
    start = today - timedelta(days=days - 1)
    rows = dict(db.execute(
        select(XpEvent.local_date, func.sum(XpEvent.amount))
        .where(XpEvent.user_id == user_id, XpEvent.local_date >= start)
        .group_by(XpEvent.local_date)
    ).all())
    return [{"date": (d := start + timedelta(days=i)).isoformat(), "xp": rows.get(d, 0)} for i in range(days)]


def practiced_days(db: Session, user_id: int, since: date) -> list[str]:
    """Learner-local days with any XP since `since` (the profile's streak calendar)."""
    return [d.isoformat() for d in db.scalars(
        select(XpEvent.local_date).where(XpEvent.user_id == user_id, XpEvent.local_date >= since)
        .distinct().order_by(XpEvent.local_date))]
