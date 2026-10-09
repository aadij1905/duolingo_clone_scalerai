"""The current learner: top-bar stats, settings, profile."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import Course, User
from ..schemas import UpdateSettings
from ..services import achievements, hearts, leaderboard, streak, xp
from ..services.course import course_view
from ..services.errors import not_found

router = APIRouter(prefix="/api/me", tags=["me"])


def me_view(db: Session, user: User, clock: Clock) -> dict:
    today = clock.today(user.timezone)
    nxt = hearts.next_heart_at(user)
    return {
        "id": user.id, "username": user.username, "display_name": user.display_name,
        "avatar_color": user.avatar_color, "timezone": user.timezone,
        "registered": user.password_hash is not None or user.google_sub is not None,
        "has_password": user.password_hash is not None, "google_email": user.email,
        "onboarded": user.onboarded,
        "course": course_view(db.get(Course, user.course_id)),
        "league": leaderboard.LEAGUES[user.league_tier],
        "league_event": getattr(user, "league_event", {}) or {},
        "xp_total": user.xp_total, "gems": user.gems,
        "hearts": user.hearts, "max_hearts": settings.max_hearts,
        "next_heart_at": nxt.isoformat() + "Z" if nxt else None,
        "streak": user.streak, "longest_streak": user.longest_streak,
        "streak_extended_today": streak.is_extended_today(user, today),
        "streak_freezes": user.streak_freezes, "max_streak_freezes": settings.max_streak_freezes,
        "heart_refill_cost": settings.heart_refill_gem_cost,  # prices live in config.py, never in the client
        "streak_event": getattr(user, "streak_event", {}) or {},
        "daily_goal_xp": user.daily_goal_xp, "daily_xp": xp.xp_on(db, user.id, today),
        "today": today.isoformat(),
    }


@router.get("")
def get_me(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return me_view(db, user, clock)


@router.patch("")
def update_me(body: UpdateSettings, user: User = Depends(current_user), db: Session = Depends(get_db),
              clock: Clock = Depends(get_clock)):
    data = body.model_dump(exclude_none=True)
    if (tz := data.pop("timezone", None)) and tz != user.timezone:
        streak.change_timezone(user, tz, clock.today(user.timezone), clock.today(tz))
    if (course_id := data.get("course_id")) and not db.get(Course, course_id):
        raise not_found("Course")
    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    return me_view(db, user, clock)


@router.get("/profile")
def profile(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    stats = achievements.learner_stats(db, user)
    return {
        "user": me_view(db, user, clock),
        "joined": user.created_at.date().isoformat(),
        "stats": stats.__dict__,
        "weekly_xp": xp.xp_last_days(db, user.id, clock.today(user.timezone)),
        "practiced_days": xp.practiced_days(db, user.id, clock.today(user.timezone).replace(day=1)),
        "achievements": achievements.list_for_user(db, user.id),
    }
