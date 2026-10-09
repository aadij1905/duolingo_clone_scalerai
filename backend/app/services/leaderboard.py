"""Weekly leagues, computed from the XP ledger.

A learner competes with everyone in their league tier plus the seeded rival
bots (so a league is never empty), ranked by XP earned since Monday 00:00 UTC.
The table is live: finish a lesson and you climb.

Promotion is settled lazily on read, like hearts and streaks: the first request
in a new week ranks the learner in the week they last played, moves them up
(top 7) or down (bottom 5), and reports it once so the UI can celebrate.
"""
import random
from datetime import datetime, time, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..models import User, XpEvent

LEAGUES = ["Bronze", "Silver", "Gold", "Sapphire", "Ruby"]
PROMOTION_ZONE = 7
DEMOTION_ZONE = 5


def week_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)


def _zone(i: int, n: int, tier: int) -> str | None:
    if i < PROMOTION_ZONE and tier < len(LEAGUES) - 1:
        return "promotion"
    if i >= n - DEMOTION_ZONE and tier > 0:
        return "demotion"
    return None


def standings(db: Session, me: User, start: datetime, end: datetime) -> list[tuple]:
    weekly_xp = (select(XpEvent.user_id, func.sum(XpEvent.amount).label("xp"))
                 .where(XpEvent.created_at >= start, XpEvent.created_at < end)
                 .group_by(XpEvent.user_id).subquery())
    xp = func.coalesce(weekly_xp.c.xp, 0)
    return db.execute(
        select(User.id, User.display_name, User.avatar_color, xp.label("xp"))
        .outerjoin(weekly_xp, weekly_xp.c.user_id == User.id)
        # Like Duolingo, you join the week's league by earning XP: idle guests never show up.
        .where(or_(User.is_bot.is_(True), User.id == me.id, and_(User.league_tier == me.league_tier, xp > 0)))
        .order_by(xp.desc(), User.id)
        .limit(30)  # ponytail: one cohort per tier; real leagues would bucket learners into groups of 30
    ).all()


def weekly(db: Session, me: User, now: datetime) -> dict:
    start, end = week_bounds(now)
    rows = standings(db, me, start, end)
    entries = [{"rank": i + 1, "user_id": uid, "name": name, "avatar_color": color, "xp": xp,
                "is_me": uid == me.id, "zone": _zone(i, len(rows), me.league_tier)}
               for i, (uid, name, color, xp) in enumerate(rows)]
    return {"league": LEAGUES[me.league_tier], "tier": me.league_tier, "ends_at": end.isoformat() + "Z",
            "entries": entries}


def settle_league(db: Session, user: User, now: datetime) -> dict:
    """Promote/demote once the week the learner last played has ended."""
    this_week = week_bounds(now)[0].date()
    if user.league_week is None or user.league_week >= this_week:
        user.league_week = user.league_week or this_week
        return {}
    start = datetime.combine(user.league_week, time())
    end = start + timedelta(days=7)
    top_up_rivals(db, end - timedelta(seconds=1))  # the bots finish that week too
    rows = standings(db, user, start, end)
    i = next(k for k, r in enumerate(rows) if r[0] == user.id)
    zone = _zone(i, len(rows), user.league_tier) if rows[i][3] > 0 or user.league_tier > 0 else None
    user.league_week = this_week
    if zone is None:
        return {}
    user.league_tier += 1 if zone == "promotion" else -1
    return {"promoted" if zone == "promotion" else "demoted": LEAGUES[user.league_tier], "rank": i + 1}


def top_up_rivals(db: Session, now: datetime) -> None:
    """Give the rival bots XP for the week containing `now` if they have none yet,
    so the league always has live competition."""
    start, end = week_bounds(now)
    rivals = db.scalars(select(User).where(User.is_bot.is_(True)).order_by(User.id)).all()
    active = set(db.scalars(select(XpEvent.user_id)
                            .where(XpEvent.created_at >= start, XpEvent.created_at < end).distinct()))
    elapsed_days = min(7, max(1, (now - start).days + 1))
    for i, rival in enumerate(rivals):
        if rival.id in active:
            continue
        rng = random.Random(f"{rival.username}-{start.date()}")
        for d in range(elapsed_days):
            when = min(now, start + timedelta(days=d, hours=rng.randint(7, 21)))
            amount = rng.choice([0, 10, 15, 20, 30, 45, 60]) if i < 10 else rng.choice([0, 0, 10])
            if amount:
                db.add(XpEvent(user_id=rival.id, amount=amount, source="lesson", local_date=when.date(), created_at=when))
                rival.xp_total += amount
    db.commit()
