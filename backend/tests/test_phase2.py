"""Multi-user accounts, three languages, the difficulty ramp, listening/speaking and the extras."""
from datetime import timedelta

from app.models import Course, Exercise, Lesson, Skill, Unit
from app.seed import STAGES

from test_api import CAFE, _play


def _first_skill(c, n=0):
    return c.get("/api/path").json()["units"][0]["skills"][n]["id"]


# ---------------------------------------------------------------- accounts

def test_each_browser_is_its_own_learner(client, guest):
    assert guest.get("/api/me").json()["xp_total"] == 0
    assert client.get("/api/me").json()["username"] == "demo"
    assert guest.get("/api/me").json()["onboarded"] is False
    from fastapi.testclient import TestClient
    from app.main import app
    assert TestClient(app).get("/api/me").status_code == 401  # no cookie, no learner


def test_register_then_login_from_another_device(guest):
    guest.patch("/api/me", json={"display_name": "Ana"})
    r = guest.post("/api/auth/register", json={"username": "ana_l", "password": "correct horse"})
    assert r.status_code == 200 and r.json()["registered"] and r.json()["username"] == "ana_l"
    assert guest.post("/api/auth/register", json={"username": "ana_2", "password": "x" * 8}).status_code == 409

    from fastapi.testclient import TestClient
    from app.main import app
    other = TestClient(app)
    assert other.post("/api/auth/login", json={"username": "ana_l", "password": "wrong pass"}).status_code == 401
    assert other.post("/api/auth/login", json={"username": "ANA_L", "password": "correct horse"}).status_code == 200
    assert other.get("/api/me").json()["display_name"] == "Ana"
    other.post("/api/auth/logout")
    assert other.get("/api/me").status_code == 401


def test_usernames_are_unique_and_validated(client, guest):
    assert guest.post("/api/auth/register", json={"username": "demo", "password": "password1"}).status_code == 409
    assert guest.post("/api/auth/register", json={"username": "no spaces", "password": "password1"}).status_code == 422
    assert guest.post("/api/auth/register", json={"username": "okname", "password": "short"}).status_code == 422


def test_guest_joins_the_league(client, guest, solve):
    s = _play(guest, solve, skill_id=_first_skill(guest))
    guest.post(f"/api/sessions/{s['id']}/complete")
    names = {e["name"] for e in client.get("/api/leaderboard").json()["entries"]}
    assert "New learner" in names


# ---------------------------------------------------------------- languages

def test_three_courses_with_their_own_path(guest, db_factory):
    courses = guest.get("/api/courses").json()
    assert [(c["language_code"], c["tts_locale"], c["word_spacing"]) for c in courses] == [
        ("es", "es-ES", True), ("fr", "fr-FR", True), ("ja", "ja-JP", False), ("hi", "hi-IN", True)]
    ja = courses[2]["id"]
    me = guest.patch("/api/me", json={"course_id": ja, "daily_goal_xp": 10, "onboarded": True}).json()
    assert me["course"]["title"] == "Japanese" and me["onboarded"]
    path = guest.get("/api/path").json()
    assert path["course"]["flag"] == "🇯🇵"
    assert guest.patch("/api/me", json={"course_id": 9999}).status_code == 404
    with db_factory() as db:  # every course's word skills are generated from the same topics
        counts = [db.query(Exercise).join(Lesson).join(Skill).join(Unit)
                  .filter(Unit.course_id == c.id, ~((Unit.position == 1) & (Skill.position == 1))).count()
                  for c in db.query(Course).all()]
    assert len(set(counts)) == 1


def test_japanese_lesson_accepts_romaji(guest, solve):
    ja = guest.get("/api/courses").json()[2]["id"]
    guest.patch("/api/me", json={"course_id": ja})
    s = guest.post("/api/sessions", json={"skill_id": _first_skill(guest)}).json()  # Hiragana
    listen = next(e for e in s["exercises"] if e["type"] == "listen_tap")
    r = guest.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": listen["id"], "value": "u"}).json()
    assert r["correct"] and r["reading"] == "u", r  # う, heard and answered in romaji; the bar shows how to say it


def test_progress_is_per_course(client, solve):
    fr = client.get("/api/courses").json()[1]
    assert fr["skills_done"] == 0
    client.patch("/api/me", json={"course_id": fr["id"]})
    states = [s["state"] for u in client.get("/api/path").json()["units"] for s in u["skills"]]
    assert states[:2] == ["active", "locked"]


# ---------------------------------------------------------------- easy start

def test_difficulty_ramp(guest, db_factory):
    with db_factory() as db:
        es = db.query(Course).filter_by(language_code="es").one()
        units = sorted(es.units, key=lambda u: u.position)
        first = sorted(units[0].skills, key=lambda sk: sk.position)
        lengths = [[len(lesson.exercises) for lesson in u.skills[-1].lessons] for u in units]
    assert first[0].title == "Letters & sounds" and first[1].title == "Basics"  # letters before words
    assert lengths == [[4, 5], [6, 6, 6], [7, 7, 7, 7]]
    assert "type" not in STAGES[0] + STAGES[1] and "type" in STAGES[3]


def test_beginner_protection_costs_no_hearts(guest):
    s = guest.post("/api/sessions", json={"skill_id": _first_skill(guest)}).json()
    assert s["no_heart_loss"] and s["exercises"][0]["prompt"].startswith("Which letter")
    for _ in range(6):
        r = guest.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": s["exercises"][0]["id"], "value": "x"})
    assert r.json()["hearts"] == 5 and r.json()["status"] == "active"
    assert guest.get("/api/me").json()["daily_goal_xp"] == 10  # Casual by default


def test_hints_are_sent_for_target_language_words(client):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    tr = next(e for e in s["exercises"] if e["type"] == "translate")
    assert any(t.get("h") for t in tr["payload"]["tokens"])


# ---------------------------------------------------------------- listening & speaking

def test_skip_only_for_listening_and_speaking(client):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    hearts = client.get("/api/me").json()["hearts"]
    speak = next(e for e in s["exercises"] if e["type"] == "speak")
    pick = next(e for e in s["exercises"] if e["type"] == "multiple_choice")
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": speak["id"], "skip": True}).json()
    assert r["correct"] and r["skipped"] and r["hearts"] == hearts
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": pick["id"], "skip": True})
    assert r.status_code == 422 and r.json()["error"] == "not_skippable"


def test_listening_and_speaking_practice(client, solve):
    for kind, types in [("listening", {"listen_tap", "listen_type"}), ("speaking", {"speak"})]:
        s = _play(client, solve, skill_id=None, mode="practice", kind=kind)
        assert len(s["exercises"]) == 8 and {e["type"] for e in s["exercises"]} <= types
        assert client.post(f"/api/sessions/{s['id']}/complete").status_code == 200
    assert client.get("/api/path").json()["units"][0]["skills"][2]["lessons_total"] == 2  # drills stay off the path


def test_typo_is_accepted_with_a_note(client, db_factory):
    s = client.post("/api/sessions", json={"skill_id": None, "mode": "practice", "kind": "listening"}).json()
    ex = next(e for e in s["exercises"] if e["type"] == "listen_type")
    with db_factory() as db:
        answer = db.get(Exercise, ex["id"]).answers[0]
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": ex["id"], "value": answer + "x"}).json()
    assert r["correct"] and r["typo"]


# ---------------------------------------------------------------- extras

def test_mistakes_review(client, solve):
    assert client.post("/api/sessions", json={"mode": "practice", "kind": "mistakes"}).json()["error"] == "no_mistakes"
    s = _play(client, solve, wrong_first=2)
    missed = {e["id"] for e in s["exercises"][:2]}
    review = client.post("/api/sessions", json={"mode": "practice", "kind": "mistakes"}).json()
    assert {e["id"] for e in review["exercises"]} == missed


def test_guidebook(client):
    unit = client.get("/api/path").json()["units"][0]
    g = client.get(f"/api/units/{unit['id']}/guidebook").json()
    assert g["title"] == unit["title"] and len(g["skills"]) == 4
    assert g["skills"][0]["phrases"][5]["text"] == "ñ"
    assert {p["kind"] for p in g["skills"][1]["phrases"]} == {"word", "sentence"}


def test_daily_quests_claim_once(client, solve):
    quests = {q["code"]: q for q in client.get("/api/quests").json()}
    assert quests["goal"]["progress"] == 0
    assert client.post("/api/quests/goal/claim").json()["error"] == "quest_incomplete"
    s = _play(client, solve)
    client.post(f"/api/sessions/{s['id']}/complete")
    quests = {q["code"]: q for q in client.get("/api/quests").json()}
    assert quests["perfect"]["progress"] == 1 and quests["lessons"]["progress"] == 1
    gems = client.get("/api/me").json()["gems"]
    r = client.post("/api/quests/perfect/claim").json()
    assert r["gems_earned"] == 20 and r["me"]["gems"] == gems + 20
    assert client.post("/api/quests/perfect/claim").json()["error"] == "already_claimed"
    assert client.post("/api/quests/nope/claim").status_code == 404


def test_league_promotion_and_demotion_at_week_rollover(client, clock, db_factory):
    from app.models import User, XpEvent
    client.get("/api/leaderboard")  # bots play this week
    with db_factory() as db:  # a huge week for the demo learner
        demo = db.query(User).filter_by(username="demo").one()
        db.add(XpEvent(user_id=demo.id, amount=5000, source="lesson", local_date=clock.now().date(), created_at=clock.now()))
        db.commit()
    assert client.get("/api/me").json()["league_event"] == {}
    clock.offset += timedelta(days=7)
    me = client.get("/api/me").json()
    assert me["league"] == "Silver" and me["league_event"]["promoted"] == "Silver"
    assert client.get("/api/me").json()["league_event"] == {}  # reported once
    assert client.get("/api/leaderboard").json()["league"] == "Silver"
    clock.offset += timedelta(days=7)  # an idle week in Silver: bottom 5, back to Bronze
    assert client.get("/api/me").json()["league_event"] == {"demoted": "Bronze", "rank": 13}


def test_streak_calendar_and_reset_keeps_login(guest, solve):
    s = _play(guest, solve, skill_id=_first_skill(guest))
    guest.post(f"/api/sessions/{s['id']}/complete")
    me = guest.get("/api/me").json()
    assert guest.get("/api/me/profile").json()["practiced_days"] == [me["today"]]
    guest.post("/api/dev/reset")
    me2 = guest.get("/api/me").json()
    assert me2["xp_total"] == 0 and me2["username"] == me["username"]


def test_accented_letters_are_distinct_answers(guest):
    fr = guest.get("/api/courses").json()[1]["id"]
    guest.patch("/api/me", json={"course_id": fr})
    s = guest.post("/api/sessions", json={"skill_id": _first_skill(guest)}).json()
    pick = s["exercises"][0]
    texts = [o["text"] for o in pick["payload"]["options"]]
    results = [guest.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": pick["id"], "value": t}).json()["correct"]
               for t in texts]
    assert results.count(True) == 1  # é is not accepted for è


def test_new_learner_practice(guest):
    r = guest.post("/api/sessions", json={"mode": "practice", "kind": "speaking"})
    assert r.status_code == 409 and r.json()["error"] == "nothing_to_practice"  # only the letters are unlocked
    ja = guest.get("/api/courses").json()[2]["id"]
    guest.patch("/api/me", json={"course_id": ja})
    s = guest.post("/api/sessions", json={"mode": "practice", "kind": "listening"}).json()
    assert len(s["exercises"]) == 8 and {e["type"] for e in s["exercises"]} == {"listen_tap"}  # kana drill


def test_google_sign_in_links_guest_then_signs_in_elsewhere(guest, monkeypatch, solve):
    import dataclasses

    from fastapi.testclient import TestClient

    import app.routers.auth as auth_router
    from app.main import app as fastapi_app
    from app.services import auth as auth_service

    assert guest.post("/api/auth/google", json={"credential": "x" * 30}).status_code == 404  # off until configured
    monkeypatch.setattr(auth_router, "settings", dataclasses.replace(auth_router.settings, google_client_id="cid"))
    claims = {"sub": "g-123", "email": "ana@example.com", "name": "Ana G", "aud": "cid", "email_verified": "true"}
    monkeypatch.setattr(auth_service, "verify_google_token", lambda credential: claims)
    assert guest.get("/api/auth/config").json() == {"google_client_id": "cid"}

    s = _play(guest, solve, skill_id=_first_skill(guest))
    guest.post(f"/api/sessions/{s['id']}/complete")
    assert guest.post("/api/auth/google", json={"credential": "x" * 30}).status_code == 200
    me = guest.get("/api/me").json()
    assert me["registered"] and me["google_email"] == "ana@example.com" and me["display_name"] == "Ana G"

    other = TestClient(fastapi_app)  # another device: same Google account, same progress
    assert other.post("/api/auth/google", json={"credential": "x" * 30}).status_code == 200
    assert other.get("/api/me").json()["xp_total"] == me["xp_total"] > 0

    claims["sub"] = "g-456"  # a signed-in account using a new Google account gets a fresh learner
    other.post("/api/auth/google", json={"credential": "x" * 30})
    assert other.get("/api/me").json()["xp_total"] == 0


def test_hindi_course(guest, db_factory, solve):
    from app.services.grading import normalize
    hi = guest.get("/api/courses").json()[3]
    assert hi["title"] == "Hindi" and hi["flag"] == "🇮🇳"
    guest.patch("/api/me", json={"course_id": hi["id"]})
    skills = [s["title"] for s in guest.get("/api/path").json()["units"][0]["skills"]]
    assert skills[:2] == ["Devanagari", "Basics"]  # the script first, then words
    for _ in range(3):  # three letter lessons unlock Basics
        played = _play(guest, solve, skill_id=_first_skill(guest))
        assert guest.post(f"/api/sessions/{played['id']}/complete").status_code == 200

    s = guest.post("/api/sessions", json={"skill_id": _first_skill(guest, 1)}).json()  # Basics, lesson 1
    listen = next(e for e in s["exercises"] if e["type"] == "listen_tap")
    with db_factory() as db:
        deva, roman = db.get(Exercise, listen["id"]).answers[:2]
    assert listen["reading"] == roman  # "how to say it" under the speaker
    for value in (deva, roman.upper()):
        r = guest.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": listen["id"], "value": value}).json()
        assert r["correct"], (value, r)
    assert normalize("पानी") != normalize("पनी")  # vowel signs matter
    assert normalize("लड़का पानी पीता है।") == "लड़का पानी पीता है"  # the danda is punctuation


def test_time_travel_is_per_learner(client, guest):
    from app.clock import get_clock
    from app.main import app as fastapi_app
    fastapi_app.dependency_overrides.pop(get_clock)  # the real per-learner clock
    today = guest.get("/api/me").json()["today"]
    assert client.post("/api/dev/time-travel", json={"days": 3}).json()["offset_days"] == 3
    assert client.get("/api/me").json()["today"] != today
    assert guest.get("/api/me").json()["today"] == today  # the other learner didn't move


def test_production_refuses_to_wipe_an_old_schema(tmp_path, monkeypatch):
    import dataclasses

    import pytest

    import app.db as db_mod
    eng = db_mod.make_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as conn:
        conn.exec_driver_sql("PRAGMA user_version = 1")
    monkeypatch.setattr(db_mod, "settings", dataclasses.replace(db_mod.settings, reset_db_on_schema_change=False))
    with pytest.raises(RuntimeError, match="Migrate it"):
        db_mod.ensure_schema(eng)


def test_idle_guests_are_not_in_the_league(client, guest, solve):
    from fastapi.testclient import TestClient
    from app.main import app as fastapi_app
    for _ in range(3):  # visitors who never play
        assert TestClient(fastapi_app).post("/api/auth/guest").status_code == 200
    names = [e["name"] for e in client.get("/api/leaderboard").json()["entries"]]
    assert "New learner" not in names and len(names) == 13  # demo + 12 bots
    assert any(e["is_me"] for e in guest.get("/api/leaderboard").json()["entries"])  # you always see yourself
    s = _play(guest, solve, skill_id=_first_skill(guest))
    guest.post(f"/api/sessions/{s['id']}/complete")
    assert "New learner" in [e["name"] for e in client.get("/api/leaderboard").json()["entries"]]
