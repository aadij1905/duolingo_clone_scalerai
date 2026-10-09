"""Learning path: course content joined with one learner's progress.

Unlock rule (linear path, like Duolingo since 2022): skills are ordered by
(unit.position, skill.position); a skill is unlocked once every earlier skill is
complete. The first incomplete unlocked skill is the "active" one.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import Course, Skill, Unit, User, UserSkillProgress
from .errors import GameError, not_found


def load_course(db: Session, course_id: int) -> Course:
    # selectinload: 3 queries total for the whole tree instead of N+1 per unit/skill.
    course = db.scalar(select(Course).where(Course.id == course_id).options(
        selectinload(Course.units).selectinload(Unit.skills).selectinload(Skill.lessons)))
    if not course:
        raise not_found("Course")
    return course


def course_view(c: Course) -> dict:
    return {"id": c.id, "title": c.title, "flag": c.flag, "language_code": c.language_code,
            "tts_locale": c.tts_locale, "word_spacing": c.word_spacing}


def _progress(db: Session, user: User) -> dict[int, UserSkillProgress]:
    return {p.skill_id: p for p in db.scalars(select(UserSkillProgress).where(UserSkillProgress.user_id == user.id))}


def list_courses(db: Session, user: User) -> list[dict]:
    """Every course with this learner's progress (each course keeps its own path)."""
    progress = _progress(db, user)
    courses = db.scalars(select(Course).order_by(Course.id).options(
        selectinload(Course.units).selectinload(Unit.skills).selectinload(Skill.lessons))).all()
    out = []
    for c in courses:
        skills = [s for u in c.units for s in u.skills]
        done = sum(1 for s in skills if s.id in progress and progress[s.id].lessons_completed >= len(s.lessons))
        out.append(course_view(c) | {"skills_done": done, "skills_total": len(skills), "current": c.id == user.course_id})
    return out


def guidebook(db: Session, unit_id: int) -> dict:
    unit = db.scalar(select(Unit).where(Unit.id == unit_id).options(selectinload(Unit.skills).selectinload(Skill.phrases)))
    if not unit:
        raise not_found("Unit")
    return {"title": unit.title, "description": unit.description, "position": unit.position,
            "skills": [{"title": s.title, "icon": s.icon,
                        "phrases": [{"kind": p.kind, "text": p.text, "translation": p.translation,
                                     "reading": p.reading, "emoji": p.emoji} for p in s.phrases]}
                       for s in unit.skills]}


def build_path(db: Session, user: User) -> dict:
    course = load_course(db, user.course_id)
    progress = _progress(db, user)

    units, previous_done = [], True  # the very first skill is always unlocked
    for unit in course.units:
        skills = []
        for skill in unit.skills:
            p = progress.get(skill.id)
            done_count = p.lessons_completed if p else 0
            total = len(skill.lessons)
            completed = done_count >= total
            state = "completed" if completed else ("active" if previous_done else "locked")
            skills.append({
                "id": skill.id, "title": skill.title, "icon": skill.icon, "state": state,
                "lessons_completed": min(done_count, total), "lessons_total": total,
                "legendary": bool(p and p.legendary),
            })
            previous_done = completed
        units.append({"id": unit.id, "position": unit.position, "title": unit.title,
                      "description": unit.description, "color": unit.color, "skills": skills})
    return {"course": course_view(course), "units": units}


def skill_state(db: Session, user: User, skill_id: int) -> dict:
    for unit in build_path(db, user)["units"]:
        for s in unit["skills"]:
            if s["id"] == skill_id:
                return s
    raise not_found("Skill")


def require_unlocked(db: Session, user: User, skill_id: int) -> dict:
    s = skill_state(db, user, skill_id)
    if s["state"] == "locked":
        raise GameError(403, "skill_locked", "Complete the previous skills to unlock this one")
    return s
