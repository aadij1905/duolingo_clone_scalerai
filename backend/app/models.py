"""Relational schema.

Content (static, shared by all learners):
    Course 1─* Unit 1─* Skill 1─* Lesson 1─* Exercise

Learner state (per user, mutable):
    User 1─* UserSkillProgress   (crowns / lesson count per skill)
    User 1─* LessonSession 1─* SessionAnswer   (one attempt at a lesson)
    User 1─* XpEvent             (append-only XP ledger -> daily goal, leaderboard)
    User *─* Achievement via UserAchievement
    User 1─* AuthSession         (one row per signed-in browser)
    User 1─* QuestClaim          (daily quest chests, one claim per day/code)

Design notes
- XP totals are denormalised onto User for fast reads, while XpEvent keeps the
  full history; the ledger is the source of truth for "XP today / this week".
- XpEvent.session_id is UNIQUE, so a lesson can never award XP twice even if the
  client retries the completion request (DB-enforced idempotency).
- User has a version column (optimistic locking): two concurrent writes to the
  same learner cannot silently overwrite each other's hearts/XP.
"""
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ExerciseType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    translate = "translate"        # build the sentence from a word bank
    match_pairs = "match_pairs"
    fill_blank = "fill_blank"
    type_answer = "type_answer"
    listen_tap = "listen_tap"      # hear it, build it from tiles
    listen_type = "listen_type"    # hear it, type it
    speak = "speak"                # read it aloud (speech recognition transcript)


# The learner may skip these ("Can't listen / speak now") without losing a heart.
SKIPPABLE = {ExerciseType.listen_tap, ExerciseType.listen_type, ExerciseType.speak}


class SessionMode(str, enum.Enum):
    lesson = "lesson"        # normal path lesson; costs hearts
    practice = "practice"    # review; refills a heart, no heart loss
    legendary = "legendary"  # timed challenge on a finished skill


class SessionStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------- content

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    language_code: Mapped[str] = mapped_column(String(8), unique=True)
    title: Mapped[str] = mapped_column(String(80))
    flag: Mapped[str] = mapped_column(String(8))
    tts_locale: Mapped[str] = mapped_column(String(16))  # speech synthesis / recognition language
    word_spacing: Mapped[bool] = mapped_column(Boolean, default=True)  # False for Japanese
    units: Mapped[list["Unit"]] = relationship(back_populates="course", order_by="Unit.position")


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("course_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    position: Mapped[int]
    title: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200))
    color: Mapped[str] = mapped_column(String(16))  # theme token used by the path UI
    course: Mapped[Course] = relationship(back_populates="units")
    skills: Mapped[list["Skill"]] = relationship(back_populates="unit", order_by="Skill.position")


class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("unit_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"))
    position: Mapped[int]
    title: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(16))
    unit: Mapped[Unit] = relationship(back_populates="skills")
    # Path lessons only: position -1 is the hidden drill lesson holding listening/speaking practice.
    lessons: Mapped[list["Lesson"]] = relationship(
        primaryjoin="and_(Skill.id == Lesson.skill_id, Lesson.position >= 0)", order_by="Lesson.position", viewonly=True)
    phrases: Mapped[list["Phrase"]] = relationship(order_by="Phrase.id", viewonly=True)


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("skill_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    position: Mapped[int]
    skill: Mapped[Skill] = relationship()
    exercises: Mapped[list["Exercise"]] = relationship(back_populates="lesson", order_by="Exercise.position")


class Exercise(Base):
    """One question. `payload` is what the client may see; `answers` never leaves the server
    (except as the 'correct solution' shown after a wrong attempt)."""
    __tablename__ = "exercises"
    __table_args__ = (UniqueConstraint("lesson_id", "position"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"))
    position: Mapped[int]
    type: Mapped[ExerciseType] = mapped_column(Enum(ExerciseType))
    prompt: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSON)
    answers: Mapped[list] = mapped_column(JSON)  # accepted answers; first one is canonical
    tts: Mapped[str | None] = mapped_column(String(200))  # target-language text to speak
    # Shown in the feedback bar after answering (kept server-side so they can't give answers away):
    meaning: Mapped[str | None] = mapped_column(String(200))  # English meaning of the target text
    reading: Mapped[str | None] = mapped_column(String(200))  # how to say it: kana · romaji, or a letter's sound
    lesson: Mapped[Lesson] = relationship(back_populates="exercises")


class Phrase(Base):
    """Guidebook entry: a key word or sentence of a skill."""
    __tablename__ = "phrases"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # word | sentence
    text: Mapped[str] = mapped_column(String(200))
    translation: Mapped[str] = mapped_column(String(200))
    reading: Mapped[str | None] = mapped_column(String(200))  # kana · romaji for Japanese
    emoji: Mapped[str | None] = mapped_column(String(16))


# ---------------------------------------------------------------- learner

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200))  # None (and no google_sub) = guest account
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)  # Google account id, if linked
    email: Mapped[str | None] = mapped_column(String(200))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)  # seeded league rivals
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    display_name: Mapped[str] = mapped_column(String(60))
    avatar_color: Mapped[str] = mapped_column(String(16), default="#1cb0f6")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"))
    xp_total: Mapped[int] = mapped_column(default=0)
    gems: Mapped[int] = mapped_column(default=500)
    hearts: Mapped[int] = mapped_column(default=5)
    hearts_updated_at: Mapped[datetime] = mapped_column(DateTime)  # anchor for lazy regeneration
    streak: Mapped[int] = mapped_column(default=0)
    longest_streak: Mapped[int] = mapped_column(default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date)  # learner-local date of last lesson
    streak_freezes: Mapped[int] = mapped_column(default=0)
    daily_goal_xp: Mapped[int] = mapped_column(default=10)  # Casual: day one hits the goal
    league_tier: Mapped[int] = mapped_column(default=0)  # index into leaderboard.LEAGUES
    league_week: Mapped[date | None] = mapped_column(Date)  # Monday of the week last settled
    clock_offset_s: Mapped[float] = mapped_column(default=0.0)  # demo time travel, per learner
    perfect_lessons: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # SQLAlchemy optimistic locking: every UPDATE adds "WHERE version = :old" and
    # raises StaleDataError if another transaction got there first.
    __mapper_args__ = {"version_id_col": version}

    progress: Mapped[list["UserSkillProgress"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserSkillProgress(Base):
    __tablename__ = "user_skill_progress"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    lessons_completed: Mapped[int] = mapped_column(default=0)
    legendary: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    user: Mapped[User] = relationship(back_populates="progress")


class LessonSession(Base):
    """A single attempt. The server owns the exercise list and grades every answer,
    so a client cannot claim XP for a lesson it did not actually pass."""
    __tablename__ = "lesson_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    lesson_id: Mapped[int | None] = mapped_column(ForeignKey("lessons.id"))
    mode: Mapped[SessionMode] = mapped_column(Enum(SessionMode))
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.active)
    exercise_ids: Mapped[list] = mapped_column(JSON)
    mistakes: Mapped[int] = mapped_column(default=0)
    no_heart_loss: Mapped[bool] = mapped_column(Boolean, default=False)  # beginner protection
    started_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    deadline: Mapped[datetime | None] = mapped_column(DateTime)  # legendary only
    result: Mapped[dict | None] = mapped_column(JSON)  # cached completion payload (idempotent replays)
    answers: Mapped[list["SessionAnswer"]] = relationship(cascade="all, delete-orphan")


class SessionAnswer(Base):
    __tablename__ = "session_answers"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("lesson_sessions.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    answer: Mapped[dict] = mapped_column(JSON)  # {"value": ...} — keeps any answer shape
    correct: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime)


class XpEvent(Base):
    __tablename__ = "xp_events"
    __table_args__ = (Index("ix_xp_user_date", "user_id", "local_date"), Index("ix_xp_created", "created_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    session_id: Mapped[str | None] = mapped_column(ForeignKey("lesson_sessions.id"), unique=True)
    amount: Mapped[int]
    source: Mapped[str] = mapped_column(String(20))
    local_date: Mapped[date] = mapped_column(Date)  # learner-local day, for the daily goal
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(String(160))
    icon: Mapped[str] = mapped_column(String(16))
    color: Mapped[str] = mapped_column(String(16))


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    achievement_id: Mapped[int] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime)


class AuthSession(Base):
    """A signed-in browser. Only the SHA-256 of the cookie token is stored."""
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


class QuestClaim(Base):
    """The primary key makes claiming a daily quest chest idempotent."""
    __tablename__ = "quest_claims"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
