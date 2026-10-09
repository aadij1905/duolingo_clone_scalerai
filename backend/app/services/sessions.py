"""The lesson loop: start -> answer* -> complete.

The server is authoritative for everything a learner could want to cheat on:
it picks the exercises, grades each answer, deducts hearts, enforces the
legendary timer, and awards XP only after every exercise was answered
correctly. Completion is idempotent: replaying /complete returns the stored
result instead of awarding XP twice (also guarded by a UNIQUE constraint).
"""
import random
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..clock import Clock
from ..config import settings
from ..models import (
    SKIPPABLE, Exercise, ExerciseType, Lesson, LessonSession, SessionAnswer, SessionMode, SessionStatus, Skill, Unit,
    User, UserSkillProgress,
)
from . import achievements, course, hearts, streak, xp
from .errors import GameError, not_found
from .grading import grade, solution_text

PRACTICE_SIZE = 8
LEGENDARY_SIZE = 10
DRILL_TYPES = {"listening": {ExerciseType.listen_tap, ExerciseType.listen_type}, "speaking": {ExerciseType.speak}}


def public_exercise(e: Exercise) -> dict:
    """Client-safe view: never includes `answers`."""
    view = {"id": e.id, "type": e.type.value, "prompt": e.prompt, "payload": e.payload, "tts": e.tts}
    if e.type in DRILL_TYPES["listening"]:
        view["reading"] = e.reading  # how it's said (romaji / kana), shown under the speaker like a dictionary
    return view


def _progress(db: Session, user: User, skill_id: int, now: datetime) -> UserSkillProgress:
    p = db.get(UserSkillProgress, (user.id, skill_id))
    if not p:
        p = UserSkillProgress(user_id=user.id, skill_id=skill_id, lessons_completed=0, legendary=False, updated_at=now)
        db.add(p)
    return p


def _session_view(db: Session, s: LessonSession, user: User) -> dict:
    exercises = {e.id: e for e in db.scalars(select(Exercise).where(Exercise.id.in_(s.exercise_ids)))}
    return {
        "id": s.id, "mode": s.mode.value, "skill_id": s.skill_id, "status": s.status.value,
        "exercises": [public_exercise(exercises[i]) for i in s.exercise_ids],
        "hearts": user.hearts, "no_heart_loss": s.no_heart_loss, "deadline": s.deadline.isoformat() + "Z" if s.deadline else None,
        "time_limit_s": settings.legendary_time_limit_s if s.mode == SessionMode.legendary else None,
        "max_mistakes": settings.legendary_max_mistakes if s.mode == SessionMode.legendary else None,
    }


def start(db: Session, user: User, clock: Clock, skill_id: int | None, mode: SessionMode, kind: str = "mix") -> dict:
    now = clock.now()
    lesson_id, free = None, False

    if mode == SessionMode.practice:
        if kind == "mistakes":
            exercise_ids = _mistakes_pool(db, user)
        elif kind in DRILL_TYPES:
            exercise_ids = _drill_pool(db, user, DRILL_TYPES[kind])
        else:
            exercise_ids = _practice_pool(db, user, skill_id)
        if not exercise_ids:
            raise GameError(409, "nothing_to_practice", "Finish a few more lessons to unlock this practice")
        skill_id = skill_id or db.get(Exercise, exercise_ids[0]).lesson.skill_id
    else:
        if skill_id is None:
            raise GameError(422, "skill_required", "skill_id is required for this mode")
        state = course.require_unlocked(db, user, skill_id)
        skill = db.get(Skill, skill_id)
        if mode == SessionMode.lesson:
            # Next lesson on the path; a completed skill replays a random one.
            idx = state["lessons_completed"] if state["state"] != "completed" else random.randrange(len(skill.lessons))
            lesson = skill.lessons[idx]
            lesson_id, exercise_ids = lesson.id, [e.id for e in lesson.exercises]
            free = lesson.id in _beginner_lessons(db, user)
            hearts.settle_hearts(user, now)
            if user.hearts <= 0 and not free:
                raise GameError(409, "out_of_hearts", "You ran out of hearts")
        else:  # legendary
            if state["state"] != "completed":
                raise GameError(403, "skill_not_completed", "Finish every lesson in this skill first")
            pool = [e.id for lesson in skill.lessons for e in lesson.exercises]
            exercise_ids = random.sample(pool, min(LEGENDARY_SIZE, len(pool)))

    s = LessonSession(user_id=user.id, skill_id=skill_id, lesson_id=lesson_id, mode=mode, exercise_ids=exercise_ids,
                      no_heart_loss=free, started_at=now, deadline=now + timedelta(seconds=settings.legendary_time_limit_s)
                      if mode == SessionMode.legendary else None)
    db.add(s)
    db.commit()
    return _session_view(db, s, user)


def _practice_pool(db: Session, user: User, skill_id: int | None) -> list[int]:
    """Exercises from lessons the learner has already finished (or the first lesson if none)."""
    path = course.build_path(db, user)
    skills = [s for u in path["units"] for s in u["skills"] if s["state"] != "locked"]
    if skill_id is not None:
        skills = [s for s in skills if s["id"] == skill_id]
        if not skills:
            raise GameError(403, "skill_locked", "That skill is locked")
    done = {s["id"]: max(1, s["lessons_completed"]) for s in skills}
    rows = db.execute(select(Exercise.id, Lesson.skill_id, Lesson.position).join(Lesson)
                      .where(Lesson.skill_id.in_(done), Lesson.position >= 0)).all()
    pool = [eid for eid, sid, pos in rows if pos < done[sid]]
    return random.sample(pool, min(PRACTICE_SIZE, len(pool)))


def _drill_pool(db: Session, user: User, types: set[ExerciseType]) -> list[int]:
    """Listening or speaking exercises from the hidden drill lessons of every unlocked skill."""
    unlocked = [s["id"] for u in course.build_path(db, user)["units"] for s in u["skills"] if s["state"] != "locked"]
    pool = list(db.scalars(select(Exercise.id).join(Lesson)
                           .where(Lesson.skill_id.in_(unlocked), Lesson.position < 0, Exercise.type.in_(types))))
    return random.sample(pool, min(PRACTICE_SIZE, len(pool)))


def _mistakes_pool(db: Session, user: User) -> list[int]:
    """The most recently missed exercises in the learner's current course."""
    last_missed = func.max(SessionAnswer.created_at)
    pool = list(db.scalars(
        select(SessionAnswer.exercise_id)
        .join(LessonSession, LessonSession.id == SessionAnswer.session_id)
        .join(Exercise, Exercise.id == SessionAnswer.exercise_id).join(Lesson).join(Skill).join(Unit)
        .where(LessonSession.user_id == user.id, SessionAnswer.correct.is_(False), Unit.course_id == user.course_id)
        .group_by(SessionAnswer.exercise_id).order_by(desc(last_missed)).limit(PRACTICE_SIZE)))
    if not pool:
        raise GameError(409, "no_mistakes", "No mistakes to review yet. Nice!")
    return pool


def _beginner_lessons(db: Session, user: User) -> set[int]:
    """The first skills of the course (letters, then Basics): they never cost hearts."""
    c = course.load_course(db, user.course_id)
    skills = [s for u in c.units for s in u.skills][:settings.beginner_free_skills]
    return {lesson.id for s in skills for lesson in s.lessons}


def _own_active(db: Session, user: User, session_id: str) -> LessonSession:
    s = db.get(LessonSession, session_id)
    if not s or s.user_id != user.id:
        raise not_found("Session")
    return s


def _check_deadline(db: Session, s: LessonSession, now: datetime) -> None:
    if s.deadline and now > s.deadline and s.status == SessionStatus.active:
        s.status = SessionStatus.failed
        db.commit()
        raise GameError(409, "time_up", "Time's up!")


def answer(db: Session, user: User, clock: Clock, session_id: str, exercise_id: int, value: Any,
           skip: bool = False) -> dict:
    now = clock.now()
    s = _own_active(db, user, session_id)
    if s.status != SessionStatus.active:
        raise GameError(409, "session_closed", f"This session is already {s.status.value}")
    if exercise_id not in s.exercise_ids:
        raise GameError(422, "wrong_exercise", "Exercise is not part of this session")
    _check_deadline(db, s, now)

    exercise = db.get(Exercise, exercise_id)
    if skip and exercise.type not in SKIPPABLE:
        raise GameError(422, "not_skippable", "Only listening and speaking exercises can be skipped")
    correct, typo = (True, False) if skip else grade(exercise, value)
    db.add(SessionAnswer(session_id=s.id, exercise_id=exercise_id,
                         answer={"skipped": True} if skip else {"value": value}, correct=correct, created_at=now))
    if not correct:
        s.mistakes += 1
        if s.mode == SessionMode.lesson and not s.no_heart_loss:
            hearts.lose_heart(user, now)
            if user.hearts == 0:
                s.status = SessionStatus.failed
        elif s.mode == SessionMode.legendary and s.mistakes > settings.legendary_max_mistakes:
            s.status = SessionStatus.failed
    db.commit()
    return {"correct": correct, "typo": typo, "skipped": skip, "solution": solution_text(exercise),
            "meaning": exercise.meaning, "reading": exercise.reading,
            "hearts": user.hearts, "status": s.status.value, "mistakes": s.mistakes}


def complete(db: Session, user: User, clock: Clock, session_id: str) -> dict:
    now = clock.now()
    today = clock.today(user.timezone)
    s = _own_active(db, user, session_id)
    if s.status == SessionStatus.completed:
        return s.result  # idempotent replay
    if s.status == SessionStatus.failed:
        raise GameError(409, "session_failed", "This session was failed")
    _check_deadline(db, s, now)

    solved = set(db.scalars(select(SessionAnswer.exercise_id).where(
        SessionAnswer.session_id == s.id, SessionAnswer.correct.is_(True))))
    if not set(s.exercise_ids) <= solved:
        raise GameError(409, "incomplete", "Answer every exercise correctly before finishing")

    perfect = s.mistakes == 0
    goal_before = xp.xp_on(db, user.id, today)
    if s.mode == SessionMode.lesson:
        earned = settings.lesson_xp + (settings.perfect_lesson_bonus_xp if perfect else 0)
        lesson = db.get(Lesson, s.lesson_id)
        p = _progress(db, user, s.skill_id, now)
        if lesson.position == p.lessons_completed:  # only the *next* lesson advances the path
            p.lessons_completed += 1
            p.updated_at = now
        if perfect:
            user.perfect_lessons += 1
    elif s.mode == SessionMode.practice:
        earned = settings.practice_xp
        hearts.gain_hearts(user, 1, now)  # practice is the free way to earn hearts back
    else:
        earned = settings.legendary_xp
        p = _progress(db, user, s.skill_id, now)
        p.legendary, p.updated_at = True, now

    xp.award_xp(db, user, earned, s.mode.value, today, now, session_id=s.id)
    gems = settings.lesson_gems
    goal_reached = goal_before < user.daily_goal_xp <= goal_before + earned
    if goal_reached:
        gems += settings.daily_goal_gems
    user.gems += gems
    streak_extended = streak.record_activity(user, today)
    db.flush()  # make this lesson visible to the achievement queries below
    new_badges = achievements.evaluate(db, user, now)

    answered = len(db.scalars(select(SessionAnswer.id).where(SessionAnswer.session_id == s.id)).all())
    s.status, s.completed_at = SessionStatus.completed, now
    s.result = {
        "xp_earned": earned, "perfect": perfect, "gems_earned": gems,
        "accuracy": round(100 * len(s.exercise_ids) / max(answered, 1)),
        "duration_s": int((now - s.started_at).total_seconds()),
        "streak": user.streak, "streak_extended": streak_extended,
        "daily_xp": goal_before + earned, "daily_goal_xp": user.daily_goal_xp, "daily_goal_reached": goal_reached,
        "hearts": user.hearts, "achievements": new_badges, "mode": s.mode.value,
    }
    try:
        db.commit()
    except IntegrityError:  # a concurrent duplicate /complete won the race
        db.rollback()
        db.refresh(s)
        return s.result
    return s.result
