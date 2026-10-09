"""Daily quests: progress is derived from today's XP ledger, and each chest can be
claimed once per day (QuestClaim's primary key enforces it)."""
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import LessonSession, QuestClaim, User, XpEvent
from . import xp
from .errors import GameError

REWARDS = {"goal": 10, "lessons": 15, "perfect": 20}  # gems per chest


def daily(db: Session, user: User, today: date) -> list[dict]:
    lessons_today = (select(func.count()).select_from(XpEvent)
                     .where(XpEvent.user_id == user.id, XpEvent.local_date == today, XpEvent.source == "lesson"))
    perfect_today = lessons_today.join(LessonSession, LessonSession.id == XpEvent.session_id).where(
        LessonSession.mistakes == 0)
    claimed = set(db.scalars(select(QuestClaim.code).where(QuestClaim.user_id == user.id, QuestClaim.day == today)))
    quests = [
        ("goal", f"Earn {user.daily_goal_xp} XP", xp.xp_on(db, user.id, today), user.daily_goal_xp),
        ("lessons", "Complete 2 lessons", db.scalar(lessons_today), 2),
        ("perfect", "Get a perfect lesson", db.scalar(perfect_today), 1),
    ]
    return [{"code": code, "title": title, "progress": min(done, target), "target": target,
             "reward": REWARDS[code], "claimed": code in claimed} for code, title, done, target in quests]


def claim(db: Session, user: User, code: str, today: date, now: datetime) -> int:
    quest = next((q for q in daily(db, user, today) if q["code"] == code), None)
    if not quest:
        raise GameError(404, "not_found", "Quest not found")
    if quest["claimed"]:
        raise GameError(409, "already_claimed", "You already opened this chest today")
    if quest["progress"] < quest["target"]:
        raise GameError(409, "quest_incomplete", "Finish the quest to open the chest")
    db.add(QuestClaim(user_id=user.id, day=today, code=code, created_at=now))
    user.gems += quest["reward"]
    try:
        db.commit()
    except IntegrityError:  # a concurrent double-click won the race
        db.rollback()
        raise GameError(409, "already_claimed", "You already opened this chest today")
    return quest["reward"]
