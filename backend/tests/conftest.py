"""Each test gets a fresh, seeded SQLite file and its own controllable Clock."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.clock import Clock, get_clock
from app.db import Base, get_db, make_engine
from app.main import app
from app.models import Exercise, ExerciseType, User
from app.seed import seed_if_empty
from app.services import auth


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def db_factory(tmp_path, clock, monkeypatch):
    import app.seed as seed_mod
    monkeypatch.setattr(seed_mod, "clock", clock)  # seed with the test's clock
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed_if_empty(db)
    yield factory
    engine.dispose()


@pytest.fixture
def client(db_factory, clock):
    def _db():
        with db_factory() as db:
            yield db
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_clock] = lambda: clock
    c = TestClient(app)  # no `with`: skip lifespan so the real DB file is untouched
    with db_factory() as db:  # signed in as the seeded demo learner
        demo = db.query(User).filter_by(username="demo").one()
        c.cookies.set(auth.COOKIE, auth.start_session(db, demo, clock.now()))
        db.commit()
    yield c
    app.dependency_overrides.clear()


@pytest.fixture
def guest(db_factory, clock, client):
    """A second browser: a brand-new guest learner."""
    c = TestClient(app)
    assert c.post("/api/auth/guest").status_code == 200
    return c


@pytest.fixture
def solve(db_factory):
    """Return the correct answer value for an exercise id (looked up server-side)."""
    def _solve(exercise_id: int):
        with db_factory() as db:
            e = db.get(Exercise, exercise_id)
            return e.payload["pairs"] if e.type == ExerciseType.match_pairs else e.answers[0]
    return _solve
