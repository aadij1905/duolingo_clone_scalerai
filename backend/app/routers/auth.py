"""Guest accounts, register, sign in / out. Sets the HttpOnly session cookie."""
import secrets

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import Credentials, GoogleCredential
from ..seed import new_user
from ..services import auth
from ..services.errors import GameError
from .me import me_view

router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_cookie(response: Response, token: str) -> None:
    response.set_cookie(auth.COOKIE, token, max_age=365 * 86400, httponly=True, samesite="lax",
                        secure=settings.cookie_secure, path="/")


@router.post("/guest")
def guest(response: Response, db: Session = Depends(get_db), clock: Clock = Depends(get_clock),
          duo_session: str | None = Cookie(None)):
    """Start as a brand-new learner (no-op if this browser is already signed in)."""
    if not auth.user_for_token(db, duo_session):
        user = new_user(db, f"guest_{secrets.token_hex(5)}", clock.now())
        set_cookie(response, auth.start_session(db, user, clock.now()))
        db.commit()
    return {"ok": True}


@router.post("/register")
def register(body: Credentials, user: User = Depends(current_user), db: Session = Depends(get_db),
             clock: Clock = Depends(get_clock)):
    """Give the current (guest) learner a username and password, keeping their progress."""
    auth.register(db, user, body.username, body.password)
    db.commit()
    return me_view(db, user, clock)


@router.post("/login")
def login(body: Credentials, response: Response, db: Session = Depends(get_db), clock: Clock = Depends(get_clock),
          duo_session: str | None = Cookie(None)):
    user = auth.login(db, body.username, body.password)
    auth.end_session(db, duo_session)
    set_cookie(response, auth.start_session(db, user, clock.now()))
    db.commit()
    return {"ok": True}


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db), duo_session: str | None = Cookie(None)):
    auth.end_session(db, duo_session)
    db.commit()
    response.delete_cookie(auth.COOKIE, path="/")
    return {"ok": True}


@router.get("/config")
def config():
    """Lets the client show "Sign in with Google" only when the server can verify it."""
    return {"google_client_id": settings.google_client_id or None}


@router.post("/google")
def google(body: GoogleCredential, response: Response, db: Session = Depends(get_db), clock: Clock = Depends(get_clock),
           duo_session: str | None = Cookie(None)):
    """Sign in with Google. A guest linking Google keeps their progress; a known Google
    account signs in to its learner; otherwise a new learner is created."""
    if not settings.google_client_id:
        raise GameError(404, "google_disabled", "Google sign-in is not configured on this server")
    claims = auth.verify_google_token(body.credential)
    current = auth.user_for_token(db, duo_session)
    user = auth.google_user(db, current, claims)
    if user is None:
        user = new_user(db, f"g_{secrets.token_hex(6)}", clock.now(), google_sub=claims["sub"], email=claims.get("email"),
                        display_name=(claims.get("name") or "New learner")[:60])
    if user is not current:
        auth.end_session(db, duo_session)
        set_cookie(response, auth.start_session(db, user, clock.now()))
    db.commit()
    return {"ok": True}
