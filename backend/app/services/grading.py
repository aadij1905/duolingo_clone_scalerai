"""Answer grading — one strategy per exercise type.

Open/closed: adding a new exercise type means registering one more grader with
@grader(...); the session service never changes. Each grader is a pure function
(exercise, raw answer) -> Grade, which makes them trivial to unit test.
"""
import re
import unicodedata
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any, NamedTuple

from ..config import settings
from ..models import Exercise, ExerciseType


class Grade(NamedTuple):
    correct: bool
    typo: bool = False  # accepted, but one letter off: the UI says "Watch out for typos"


Grader = Callable[[Exercise, Any], Grade]
_GRADERS: dict[ExerciseType, Grader] = {}


def grader(*kinds: ExerciseType):
    def register(fn: Grader) -> Grader:
        for k in kinds:
            _GRADERS[k] = fn
        return fn
    return register


def normalize(text: str) -> str:
    """Forgiving comparison like Duolingo's: ignore case, Latin accents, punctuation, extra spaces.
    Japanese voicing marks (が vs か) and Hindi vowel signs (पानी vs पनी) are meaningful, so only
    marks on Latin letters are dropped."""
    text = unicodedata.normalize("NFD", unicodedata.normalize("NFKC", str(text)))  # NFKC folds full-width romaji
    kept: list[str] = []
    for c in text:
        if unicodedata.combining(c) and kept and kept[-1] < "ɐ":
            continue
        kept.append(c)
    text = unicodedata.normalize("NFC", "".join(kept))
    # Only punctuation and symbols become spaces: Devanagari vowel signs aren't \w but carry meaning.
    text = "".join(" " if unicodedata.category(c)[0] in "PS" else c for c in text.lower())
    return " ".join(text.split())


def _squash(text: str) -> str:
    """Spaces don't matter either: Japanese is written without them, tiles join with them."""
    return normalize(text).replace(" ", "")


def one_edit_apart(a: str, b: str) -> bool:
    """True if a and b differ by exactly one insert, delete or substitution."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i + (len(a) == len(b)):] == b[i + 1:]


def _accepted(exercise: Exercise) -> list[str]:
    return [_squash(a) for a in exercise.answers]


@grader(ExerciseType.multiple_choice)
def _choice(exercise: Exercise, answer: Any) -> Grade:
    """Options come from the server, so compare exactly: é, è and ê are different answers."""
    return Grade(isinstance(answer, str) and answer.strip() in exercise.answers)


@grader(ExerciseType.translate, ExerciseType.fill_blank, ExerciseType.listen_tap)
def _exact(exercise: Exercise, answer: Any) -> Grade:
    return Grade(isinstance(answer, str) and _squash(answer) in _accepted(exercise))


@grader(ExerciseType.type_answer, ExerciseType.listen_type)
def _typed(exercise: Exercise, answer: Any) -> Grade:
    if not isinstance(answer, str):
        return Grade(False)
    given = _squash(answer)
    if given in _accepted(exercise):
        return Grade(True)
    typo = len(given) >= 4 and any(one_edit_apart(given, a) for a in _accepted(exercise))
    return Grade(typo, typo)


@grader(ExerciseType.speak)
def _spoken(exercise: Exercise, answer: Any) -> Grade:
    """Speech recognition is noisy: accept a transcript that is mostly the same text."""
    if not isinstance(answer, str) or not answer.strip():
        return Grade(False)
    given = _squash(answer)
    return Grade(any(SequenceMatcher(None, given, a).ratio() >= settings.speak_min_similarity
                     for a in _accepted(exercise)))


@grader(ExerciseType.match_pairs)
def _pairs(exercise: Exercise, answer: Any) -> Grade:
    """Answer is the list of [left, right] pairs the learner matched; order doesn't matter."""
    if not isinstance(answer, list):
        return Grade(False)
    try:
        given = {(normalize(a), normalize(b)) for a, b in answer}
    except (TypeError, ValueError):
        return Grade(False)
    return Grade(given == {(normalize(a), normalize(b)) for a, b in exercise.payload["pairs"]})


def grade(exercise: Exercise, answer: Any) -> Grade:
    return _GRADERS[exercise.type](exercise, answer)


def solution_text(exercise: Exercise) -> str:
    """What the feedback bar shows as the correct solution."""
    if exercise.type == ExerciseType.match_pairs:
        return ", ".join(f"{a} = {b}" for a, b in exercise.payload["pairs"])
    return exercise.answers[0]
