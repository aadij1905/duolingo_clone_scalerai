"""Lesson sessions: the core lesson loop."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import StartSession, SubmitAnswer
from ..services import sessions

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=status.HTTP_201_CREATED)
def start(body: StartSession, user: User = Depends(current_user), db: Session = Depends(get_db),
          clock: Clock = Depends(get_clock)):
    return sessions.start(db, user, clock, body.skill_id, body.mode, body.kind)


@router.post("/{session_id}/answers")
def answer(session_id: str, body: SubmitAnswer, user: User = Depends(current_user),
           db: Session = Depends(get_db), clock: Clock = Depends(get_clock)):
    return sessions.answer(db, user, clock, session_id, body.exercise_id, body.value, body.skip)


@router.post("/{session_id}/complete")
def complete(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db),
             clock: Clock = Depends(get_clock)):
    return sessions.complete(db, user, clock, session_id)
