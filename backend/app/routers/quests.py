"""Daily quests and their chests."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services import quests
from .me import me_view

router = APIRouter(prefix="/api/quests", tags=["quests"])


@router.get("")
def list_quests(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return quests.daily(db, user, clock.today(user.timezone))


@router.post("/{code}/claim")
def claim(code: str, user: User = Depends(current_user), db: Session = Depends(get_db),
          clock: Clock = Depends(get_clock)):
    gems = quests.claim(db, user, code, clock.today(user.timezone), clock.now())
    return {"gems_earned": gems, "me": me_view(db, user, clock)}
