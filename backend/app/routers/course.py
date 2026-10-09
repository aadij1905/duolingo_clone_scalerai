"""Courses and the learning path (units -> skills) with this learner's lock/progress state."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import current_user
from ..models import User
from ..services import course

router = APIRouter(prefix="/api", tags=["course"])


@router.get("/path")
def get_path(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return course.build_path(db, user)


@router.get("/courses")
def get_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return course.list_courses(db, user)


@router.get("/units/{unit_id}/guidebook")
def get_guidebook(unit_id: int, _: User = Depends(current_user), db: Session = Depends(get_db)):
    return course.guidebook(db, unit_id)
