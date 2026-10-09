"""Unit tests for the pure game rules (no HTTP, no DB)."""
from datetime import date, datetime, timedelta

from app.config import settings
from app.models import Exercise, ExerciseType, User
from app.services import hearts, streak
from app.services.grading import grade, normalize, one_edit_apart

T0 = datetime(2026, 1, 5, 12, 0)


def _user(**kw) -> User:
    base = dict(hearts=5, hearts_updated_at=T0, streak=0, longest_streak=0, last_active_date=None, streak_freezes=0)
    return User(**{**base, **kw})


# ---------------------------------------------------------------- grading

def test_normalize_is_forgiving():
    assert normalize("¿Cómo   ESTÁS?") == "como estas"
    assert normalize("The boy drinks water.") == normalize("the boy drinks water")


def test_text_grading_accepts_alternates_and_ignores_accents():
    e = Exercise(type=ExerciseType.type_answer, payload={}, answers=["El niño bebe agua.", "El chico bebe agua"])
    assert grade(e, "el nino bebe agua").correct
    assert grade(e, "El chico bebe agua!").correct
    assert not grade(e, "El niño come agua").correct
    assert not grade(e, ["not", "a string"]).correct


def test_match_pairs_order_does_not_matter():
    e = Exercise(type=ExerciseType.match_pairs, payload={"pairs": [["hola", "hello"], ["adiós", "goodbye"]]}, answers=[])
    assert grade(e, [["adios", "goodbye"], ["hola", "hello"]]).correct
    assert not grade(e, [["hola", "goodbye"], ["adiós", "hello"]]).correct
    assert not grade(e, [["hola", "hello"]]).correct
    assert not grade(e, "hola").correct


def test_typo_tolerance_is_one_letter():
    assert one_edit_apart("manzana", "manzama") and one_edit_apart("manzana", "manzan")
    assert one_edit_apart("pan", "plan") and not one_edit_apart("pan", "pan")
    assert not one_edit_apart("manzana", "mansama")
    e = Exercise(type=ExerciseType.type_answer, payload={}, answers=["La manzana."])
    assert grade(e, "la manzanna") == (True, True)
    assert grade(e, "la manzana") == (True, False)
    assert not grade(e, "la mansama").correct
    tiles = Exercise(type=ExerciseType.translate, payload={}, answers=["La manzana."])
    assert not grade(tiles, "la manzanna").correct  # word banks have no typos


def test_japanese_accepts_kanji_kana_or_romaji_and_keeps_voicing():
    e = Exercise(type=ExerciseType.listen_type, payload={},
                 answers=["男の子は水を飲みます", "おとこのこはみずをのみます", "otokonoko wa mizu o nomimasu"])
    assert grade(e, "男の子 は 水 を 飲みます").correct  # tiles join with spaces
    assert grade(e, "おとこのこはみずをのみます").correct
    assert grade(e, "Otokonoko wa mizu o nomimasu.").correct
    assert grade(e, "ｏｔｏｋｏｎｏｋｏ wa mizu o nomimasu").correct  # full-width romaji from an IME
    assert normalize("が") != normalize("か")


def test_speaking_is_graded_by_similarity():
    e = Exercise(type=ExerciseType.speak, payload={}, answers=["La mujer come una manzana."])
    assert grade(e, "la mujer come una manzana").correct
    assert grade(e, "la mujer come manzana").correct  # recognition dropped a word
    assert not grade(e, "el perro bebe agua").correct
    assert not grade(e, "").correct


# ---------------------------------------------------------------- hearts

def test_hearts_regenerate_lazily_and_keep_partial_progress():
    u = _user()
    hearts.lose_heart(u, T0)
    hearts.lose_heart(u, T0)
    assert u.hearts == 3 and u.hearts_updated_at == T0
    regen = timedelta(minutes=settings.heart_regen_minutes)
    hearts.settle_hearts(u, T0 + regen * 1.5)
    assert u.hearts == 4
    assert u.hearts_updated_at == T0 + regen  # the half interval is kept
    hearts.settle_hearts(u, T0 + regen * 10)
    assert u.hearts == settings.max_hearts and hearts.next_heart_at(u) is None


def test_hearts_never_negative():
    u = _user(hearts=0)
    hearts.lose_heart(u, T0)
    assert u.hearts == 0


# ---------------------------------------------------------------- streak

def test_streak_extends_once_per_day():
    u = _user(streak=3, last_active_date=date(2026, 1, 4))
    assert streak.record_activity(u, date(2026, 1, 5)) is True
    assert u.streak == 4
    assert streak.record_activity(u, date(2026, 1, 5)) is False
    assert u.streak == 4 and u.longest_streak == 4


def test_missed_day_breaks_streak_without_freeze():
    u = _user(streak=10, last_active_date=date(2026, 1, 1))
    assert streak.settle_streak(u, date(2026, 1, 3)) == {"streak_lost": 10}
    assert u.streak == 0
    streak.record_activity(u, date(2026, 1, 3))
    assert u.streak == 1


def test_freeze_covers_missed_day_automatically():
    u = _user(streak=10, last_active_date=date(2026, 1, 1), streak_freezes=1)
    assert streak.settle_streak(u, date(2026, 1, 3)) == {"freezes_used": 1}
    assert u.streak == 10 and u.streak_freezes == 0
    streak.record_activity(u, date(2026, 1, 3))
    assert u.streak == 11


def test_not_enough_freezes_still_breaks():
    u = _user(streak=10, last_active_date=date(2026, 1, 1), streak_freezes=1)
    streak.settle_streak(u, date(2026, 1, 4))  # two missed days, one freeze
    assert u.streak == 0 and u.streak_freezes == 1
