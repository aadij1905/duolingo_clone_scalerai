"""End-to-end API tests: the lesson loop and gamification through HTTP."""
from datetime import timedelta

from app.config import settings

LETTERS = 1   # completed (every course starts with its alphabet)
CAFE = 4      # active skill for the seeded demo learner (lesson 2 of 2 is next)
FAMILY = 5    # locked
BASICS = 2    # completed


def _skill(client, skill_id):
    return next(s for u in client.get("/api/path").json()["units"] for s in u["skills"] if s["id"] == skill_id)


def _play(client, solve, skill_id=CAFE, mode="lesson", wrong_first=0, kind="mix"):
    """Start a session, optionally miss `wrong_first` answers, then solve everything."""
    s = client.post("/api/sessions", json={"skill_id": skill_id, "mode": mode, "kind": kind})
    assert s.status_code == 201, s.text
    s = s.json()
    for ex in s["exercises"][:wrong_first]:
        r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": ex["id"], "value": "zzz wrong"})
        assert r.json()["correct"] is False
    for ex in s["exercises"]:
        r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": ex["id"], "value": solve(ex["id"])})
        assert r.json()["correct"] is True, (ex, r.json())
    return s


def test_seeded_path_states(client):
    states = [(s["id"], s["state"]) for u in client.get("/api/path").json()["units"] for s in u["skills"]]
    assert states[:5] == [(1, "completed"), (2, "completed"), (3, "completed"), (4, "active"), (5, "locked")]


def test_answers_never_sent_to_client(client):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    assert len(s["exercises"]) == 5  # unit 1, lesson 2: still a short lesson
    assert all("answers" not in e for e in s["exercises"])
    assert {e["type"] for e in s["exercises"]} == {"multiple_choice", "translate", "match_pairs", "fill_blank", "speak"}


def test_full_lesson_awards_xp_streak_and_progress(client, solve):
    before = client.get("/api/me").json()
    s = _play(client, solve)
    result = client.post(f"/api/sessions/{s['id']}/complete").json()

    assert result["xp_earned"] == settings.lesson_xp + settings.perfect_lesson_bonus_xp
    assert result["perfect"] and result["streak_extended"]
    assert result["streak"] == before["streak"] + 1
    assert result["accuracy"] == 100
    me = client.get("/api/me").json()
    assert me["xp_total"] == before["xp_total"] + result["xp_earned"]
    assert me["streak_extended_today"] is True
    assert _skill(client, CAFE)["lessons_completed"] == 2


def test_complete_is_idempotent(client, solve):
    s = _play(client, solve)
    first = client.post(f"/api/sessions/{s['id']}/complete").json()
    xp_after_first = client.get("/api/me").json()["xp_total"]
    second = client.post(f"/api/sessions/{s['id']}/complete").json()
    assert first == second
    assert client.get("/api/me").json()["xp_total"] == xp_after_first


def test_cannot_complete_without_answering(client):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    r = client.post(f"/api/sessions/{s['id']}/complete")
    assert r.status_code == 409 and r.json()["error"] == "incomplete"


def test_wrong_answer_costs_a_heart_and_no_perfect_bonus(client, solve):
    hearts = client.get("/api/me").json()["hearts"]
    s = _play(client, solve, wrong_first=1)
    result = client.post(f"/api/sessions/{s['id']}/complete").json()
    assert result["hearts"] == hearts - 1
    assert result["xp_earned"] == settings.lesson_xp and not result["perfect"]
    assert result["accuracy"] < 100


def test_out_of_hearts_fails_lesson_then_practice_earns_one_back(client, solve):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    ex = s["exercises"][0]
    status = None
    for _ in range(10):
        status = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": ex["id"], "value": "nope"}).json()
        if status["status"] == "failed":
            break
    assert status["hearts"] == 0 and status["status"] == "failed"
    assert client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": ex["id"], "value": "x"}).status_code == 409

    r = client.post("/api/sessions", json={"skill_id": CAFE})
    assert r.status_code == 409 and r.json()["error"] == "out_of_hearts"

    p = _play(client, solve, skill_id=None, mode="practice")
    result = client.post(f"/api/sessions/{p['id']}/complete").json()
    assert result["hearts"] == 1 and result["xp_earned"] == settings.practice_xp


def test_hearts_regenerate_over_time(client, clock):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": s["exercises"][0]["id"], "value": "no"})
    hearts = client.get("/api/me").json()["hearts"]
    clock.offset += timedelta(minutes=settings.heart_regen_minutes * 10)
    assert client.get("/api/me").json()["hearts"] == settings.max_hearts > hearts


def test_locked_skill_is_rejected(client):
    r = client.post("/api/sessions", json={"skill_id": FAMILY})
    assert r.status_code == 403 and r.json()["error"] == "skill_locked"


def test_finishing_a_skill_unlocks_the_next(client, solve):
    s = _play(client, solve)  # Café has 2 lessons; demo finished 1
    client.post(f"/api/sessions/{s['id']}/complete")
    assert _skill(client, CAFE)["state"] == "completed"
    assert _skill(client, FAMILY)["state"] == "active"


def test_legendary_challenge(client, solve, clock):
    assert client.post("/api/sessions", json={"skill_id": CAFE, "mode": "legendary"}).status_code == 403

    s = _play(client, solve, skill_id=BASICS, mode="legendary")
    assert s["time_limit_s"] == settings.legendary_time_limit_s
    result = client.post(f"/api/sessions/{s['id']}/complete").json()
    assert result["xp_earned"] == settings.legendary_xp
    assert _skill(client, BASICS)["legendary"] is True
    assert any(a["code"] == "legendary" for a in result["achievements"])

    # running out of time fails the challenge
    s = client.post("/api/sessions", json={"skill_id": BASICS, "mode": "legendary"}).json()
    clock.offset += timedelta(seconds=settings.legendary_time_limit_s + 1)
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": s["exercises"][0]["id"], "value": "x"})
    assert r.status_code == 409 and r.json()["error"] == "time_up"


def test_legendary_fails_after_too_many_mistakes(client):
    s = client.post("/api/sessions", json={"skill_id": BASICS, "mode": "legendary"}).json()
    hearts = client.get("/api/me").json()["hearts"]
    last = None
    for _ in range(settings.legendary_max_mistakes + 1):
        last = client.post(f"/api/sessions/{s['id']}/answers",
                           json={"exercise_id": s["exercises"][0]["id"], "value": "x"}).json()
    assert last["status"] == "failed"
    assert client.get("/api/me").json()["hearts"] == hearts  # legendary never costs hearts


def test_daily_goal_bonus_gems(client, solve):
    me = client.get("/api/me").json()
    assert me["daily_xp"] == 0 and me["daily_goal_xp"] == 20
    s1 = _play(client, solve)
    r1 = client.post(f"/api/sessions/{s1['id']}/complete").json()
    assert not r1["daily_goal_reached"] and r1["gems_earned"] == settings.lesson_gems
    s2 = _play(client, solve, skill_id=FAMILY)
    r2 = client.post(f"/api/sessions/{s2['id']}/complete").json()
    assert r2["daily_goal_reached"] and r2["gems_earned"] == settings.lesson_gems + settings.daily_goal_gems
    unlocked = {a["code"] for a in client.get("/api/me/profile").json()["achievements"] if a["unlocked_at"]}
    assert "goal_getter" in unlocked


def test_streak_freeze_and_break_via_time_travel(client, solve, clock):
    # Demo learner: streak 4, last active yesterday, 1 freeze equipped.
    clock.offset += timedelta(days=1)  # skipped "today": tomorrow the freeze covers it
    me = client.get("/api/me").json()
    assert me["streak"] == 4 and me["streak_freezes"] == 0 and me["streak_event"] == {"freezes_used": 1}

    clock.offset += timedelta(days=2)  # miss another day with no freeze -> broken
    me = client.get("/api/me").json()
    assert me["streak"] == 0 and me["streak_event"] == {"streak_lost": 4}

    s = _play(client, solve)
    assert client.post(f"/api/sessions/{s['id']}/complete").json()["streak"] == 1


def test_shop(client):
    me = client.get("/api/me").json()
    r = client.post("/api/shop/streak-freeze")
    assert r.status_code == 200 and r.json()["streak_freezes"] == 2
    assert r.json()["gems"] == me["gems"] - settings.streak_freeze_gem_cost
    assert client.post("/api/shop/streak-freeze").json()["error"] == "freeze_limit"

    r = client.post("/api/shop/heart-refill")  # demo starts with 4/5 hearts
    assert r.status_code == 200 and r.json()["hearts"] == settings.max_hearts
    assert client.post("/api/shop/heart-refill").json()["error"] == "hearts_full"


def test_not_enough_gems(client, db_factory):
    from app.models import User
    with db_factory() as db:
        db.query(User).filter_by(username="demo").update({"gems": 10})
        db.commit()
    r = client.post("/api/shop/streak-freeze")
    assert r.status_code == 402 and r.json()["error"] == "not_enough_gems"


def test_leaderboard_updates_live(client, solve):
    def my_xp():
        return next(e for e in client.get("/api/leaderboard").json()["entries"] if e["is_me"])["xp"]
    before = my_xp()
    s = _play(client, solve)
    gained = client.post(f"/api/sessions/{s['id']}/complete").json()["xp_earned"]
    assert my_xp() == before + gained
    board = client.get("/api/leaderboard").json()
    assert board["league"] == "Bronze" and len(board["entries"]) == 13  # demo + 12 bots
    xps = [e["xp"] for e in board["entries"]]
    assert xps == sorted(xps, reverse=True)


def test_settings_validation(client):
    assert client.patch("/api/me", json={"daily_goal_xp": 15}).status_code == 422
    assert client.patch("/api/me", json={"timezone": "Mars/Base"}).status_code == 422
    r = client.patch("/api/me", json={"daily_goal_xp": 50, "timezone": "Asia/Kolkata", "display_name": "Aadi"})
    assert r.status_code == 200 and r.json()["daily_goal_xp"] == 50 and r.json()["display_name"] == "Aadi"


def test_profile(client):
    p = client.get("/api/me/profile").json()
    assert p["stats"]["lessons_done"] == 7 and p["stats"]["skills_done"] == 3
    assert p["practiced_days"]
    assert len(p["weekly_xp"]) == 7
    unlocked = {a["code"] for a in p["achievements"] if a["unlocked_at"]}
    assert {"first_lesson", "wildfire_3", "perfectionist"} <= unlocked


def test_answer_validation(client):
    s = client.post("/api/sessions", json={"skill_id": CAFE}).json()
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": 999999, "value": "x"})
    assert r.status_code == 422
    r = client.post(f"/api/sessions/{s['id']}/answers", json={"exercise_id": s["exercises"][0]["id"], "value": "x" * 500})
    assert r.status_code == 422
    assert client.post("/api/sessions/nope/complete").status_code == 404


def test_timezone_change_does_not_cost_a_streak_day(client, clock):
    clock.offset = timedelta(hours=22 - clock.now().hour)  # 22:00 UTC: already "tomorrow" in Asia/Tokyo
    before = client.get("/api/me").json()
    me = client.patch("/api/me", json={"timezone": "Asia/Tokyo"}).json()
    assert me["today"] != before["today"]
    me = client.get("/api/me").json()
    assert me["streak"] == before["streak"] and me["streak_freezes"] == before["streak_freezes"]
