"""Demo/testing controls: simulate days passing, reset progress, sign in as the
sample learner. Mounted only when ENABLE_DEV_ROUTES=1. Everything here acts on the
signed-in learner only, so it is safe on a shared demo."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import TimeTravel
from ..seed import reset_user
from ..services import auth
from .auth import set_cookie

router = APIRouter(prefix="/api/dev", tags=["dev"])


@router.get("/clock")
def get_clock_state(clock: Clock = Depends(get_clock)):
    return {"now": clock.now().isoformat() + "Z", "offset_days": clock.offset.total_seconds() / 86400}


@router.post("/time-travel")
def time_travel(body: TimeTravel, user: User = Depends(current_user), db: Session = Depends(get_db),
                clock: Clock = Depends(get_clock)):
    clock.travel(body.days)
    user.clock_offset_s = clock.offset.total_seconds()
    db.commit()
    return get_clock_state(clock)


@router.post("/reset")
def reset(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    """Wipe the signed-in learner's progress."""
    clock.reset()
    reset_user(db, user, clock.now())
    return {"ok": True}


@router.post("/demo")
def demo_login(response: Response, db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    """Sign in as the seeded sample learner (mid-way through Spanish unit 1)."""
    user = db.scalar(select(User).where(User.username == settings.default_username))
    set_cookie(response, auth.start_session(db, user, clock.now()))
    db.commit()
    return {"ok": True}
