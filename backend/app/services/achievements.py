"""Achievements: declarative rules evaluated after each lesson.

DEFINITIONS is the single source of truth — the seed script writes these rows,
and `evaluate` runs each rule's check against the learner's stats. Adding a
badge is one line here; nothing else changes.
"""
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    Achievement, Lesson, LessonSession, SessionMode, SessionStatus, User, UserAchievement,
    UserSkillProgress, XpEvent,
)


@dataclass(frozen=True)
class LearnerStats:
    xp_total: int
    streak: int
    longest_streak: int
    lessons_done: int
    skills_done: int
    perfect_lessons: int
    legendary_skills: int
    goal_days: int  # days on which the daily goal was met


def learner_stats(db: Session, user: User) -> LearnerStats:
    lessons_done = db.scalar(select(func.count()).select_from(LessonSession).where(
        LessonSession.user_id == user.id, LessonSession.status == SessionStatus.completed,
        LessonSession.mode == SessionMode.lesson))
    lesson_counts = (select(Lesson.skill_id, func.count().label("n")).where(Lesson.position >= 0)
                     .group_by(Lesson.skill_id).subquery())
    skills_done = db.scalar(
        select(func.count()).select_from(UserSkillProgress)
        .join(lesson_counts, lesson_counts.c.skill_id == UserSkillProgress.skill_id)
        .where(UserSkillProgress.user_id == user.id, UserSkillProgress.lessons_completed >= lesson_counts.c.n))
    legendary = db.scalar(select(func.count()).select_from(UserSkillProgress).where(
        UserSkillProgress.user_id == user.id, UserSkillProgress.legendary.is_(True)))
    per_day = (select(XpEvent.local_date).where(XpEvent.user_id == user.id)
               .group_by(XpEvent.local_date).having(func.sum(XpEvent.amount) >= user.daily_goal_xp).subquery())
    goal_days = db.scalar(select(func.count()).select_from(per_day))
    return LearnerStats(user.xp_total, user.streak, user.longest_streak, lessons_done, skills_done,
                        user.perfect_lessons, legendary, goal_days)


@dataclass(frozen=True)
class AchievementDef:
    code: str
    title: str
    description: str
    icon: str
    color: str
    check: Callable[[LearnerStats], bool]


DEFINITIONS: list[AchievementDef] = [
    AchievementDef("first_lesson", "First Steps", "Complete your first lesson", "🐣", "#58cc02", lambda s: s.lessons_done >= 1),
    AchievementDef("wildfire_3", "Wildfire I", "Reach a 3 day streak", "🔥", "#ff9600", lambda s: s.longest_streak >= 3),
    AchievementDef("wildfire_7", "Wildfire II", "Reach a 7 day streak", "🔥", "#ff4b4b", lambda s: s.longest_streak >= 7),
    AchievementDef("sage_100", "Sage I", "Earn 100 XP", "⚡", "#ffc800", lambda s: s.xp_total >= 100),
    AchievementDef("sage_500", "Sage II", "Earn 500 XP", "⚡", "#ff9600", lambda s: s.xp_total >= 500),
    AchievementDef("sage_1000", "Sage III", "Earn 1000 XP", "⚡", "#ce82ff", lambda s: s.xp_total >= 1000),
    AchievementDef("perfectionist", "Sharpshooter", "Finish a lesson with no mistakes", "🎯", "#1cb0f6", lambda s: s.perfect_lessons >= 1),
    AchievementDef("scholar", "Scholar", "Complete 3 skills", "📚", "#2b70c9", lambda s: s.skills_done >= 3),
    AchievementDef("legendary", "Legendary", "Pass a Legendary challenge", "👑", "#ffc800", lambda s: s.legendary_skills >= 1),
    AchievementDef("goal_getter", "Goal Getter", "Meet your daily goal", "🏆", "#58cc02", lambda s: s.goal_days >= 1),
]
_BY_CODE = {d.code: d for d in DEFINITIONS}


def evaluate(db: Session, user: User, now: datetime) -> list[dict]:
    """Unlock every newly satisfied achievement; return them for celebration toasts."""
    owned = set(db.scalars(select(UserAchievement.achievement_id).where(UserAchievement.user_id == user.id)))
    candidates = [a for a in db.scalars(select(Achievement)) if a.id not in owned and a.code in _BY_CODE]
    if not candidates:
        return []
    stats = learner_stats(db, user)
    unlocked = []
    for a in candidates:
        if _BY_CODE[a.code].check(stats):
            db.add(UserAchievement(user_id=user.id, achievement_id=a.id, unlocked_at=now))
            unlocked.append({"code": a.code, "title": a.title, "description": a.description,
                             "icon": a.icon, "color": a.color})
    return unlocked


def list_for_user(db: Session, user_id: int) -> list[dict]:
    unlocked = dict(db.execute(select(UserAchievement.achievement_id, UserAchievement.unlocked_at)
                               .where(UserAchievement.user_id == user_id)).all())
    return [{"code": a.code, "title": a.title, "description": a.description, "icon": a.icon, "color": a.color,
             "unlocked_at": unlocked.get(a.id)} for a in db.scalars(select(Achievement).order_by(Achievement.id))]

