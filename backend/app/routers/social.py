"""Leaderboard (seeded rivals, live weekly XP)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services import leaderboard

router = APIRouter(prefix="/api", tags=["social"])


@router.get("/leaderboard")
def get_leaderboard(user: User = Depends(current_user), db: Session = Depends(get_db),
                    clock: Clock = Depends(get_clock)):
    leaderboard.top_up_rivals(db, clock.now())  # simulated rivals keep playing each new week
    return leaderboard.weekly(db, user, clock.now())
