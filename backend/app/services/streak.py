"""Streak: consecutive learner-local days with at least one completed lesson.

Like hearts, the streak is repaired lazily on read (settle_streak):
- missed days are covered by equipped streak freezes, auto-applied, one per day
  (a finite, visible token — scarcity is what keeps the streak meaningful);
- if there aren't enough freezes the streak resets to 0.
"""
from datetime import date, timedelta

from ..models import User


def settle_streak(user: User, today: date) -> dict:
    """Apply freezes / break the streak for days missed before `today`.
    Returns what happened so the UI can tell the learner once."""
    if not user.last_active_date or user.streak == 0:
        return {}
    missed = (today - user.last_active_date).days - 1  # days with no activity strictly between
    if missed <= 0:
        return {}
    if user.streak_freezes >= missed:
        user.streak_freezes -= missed
        user.last_active_date = today - timedelta(days=1)  # frozen days count as "kept", not as +1
        return {"freezes_used": missed}
    lost = user.streak
    user.streak = 0
    return {"streak_lost": lost}


def record_activity(user: User, today: date) -> bool:
    """Call when a lesson is completed. Returns True if this extended the streak today."""
    settle_streak(user, today)
    if user.last_active_date == today:
        return False
    if user.last_active_date == today - timedelta(days=1) and user.streak > 0:
        user.streak += 1
    else:
        user.streak = 1
    user.last_active_date = today
    user.longest_streak = max(user.longest_streak, user.streak)
    return True


def is_extended_today(user: User, today: date) -> bool:
    return user.last_active_date == today


def change_timezone(user: User, tz: str, old_today: date, new_today: date) -> None:
    """Moving to a new timezone shifts the learner's calendar, not their history:
    shift last_active_date by the same number of days so travelling (or the
    browser reporting its timezone for the first time) never costs a streak day."""
    if user.last_active_date and new_today != old_today:
        user.last_active_date += new_today - old_today
    user.timezone = tz
