"""Gem shop: heart refill and streak freeze (gems are mocked currency)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services import shop
from .me import me_view

router = APIRouter(prefix="/api/shop", tags=["shop"])


@router.get("")
def items():
    return {
        "heart_refill": {"cost": settings.heart_refill_gem_cost},
        "streak_freeze": {"cost": settings.streak_freeze_gem_cost, "max": settings.max_streak_freezes},
    }


@router.post("/heart-refill")
def refill(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    shop.refill_hearts(user, clock)
    db.commit()
    return me_view(db, user, clock)


@router.post("/streak-freeze")
def freeze(user: User = Depends(current_user), db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    shop.buy_streak_freeze(user)
    db.commit()
    return me_view(db, user, clock)
