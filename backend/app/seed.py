"""Seed data: one course per language (built from the shared topics in content.py),
the demo learner with some progress, and league rival bots.

Exercises are *generated* from small per-skill word/sentence lists. The generator
takes a difficulty stage, so the first lessons are short and gentle and later
units add typing, listening and speaking. It is deterministic (seeded RNG), so
every fresh database looks the same.

Run directly to rebuild the database:  python -m app.seed
"""
import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .clock import clock
from .config import settings
from .content import ALPHABET, ALTERNATES, COURSE, GLOSSARY, HINDI, LANGUAGES, SCRIPTS
from .models import (
    Achievement, AuthSession, Course, Exercise, ExerciseType as T, Lesson, LessonSession, Phrase, QuestClaim,
    SessionAnswer, SessionMode, SessionStatus, Skill, Unit, User, UserAchievement, UserSkillProgress, XpEvent,
)
from .services import achievements
from .services.leaderboard import top_up_rivals, week_bounds

LESSONS_PER_UNIT = {1: 2, 2: 3, 3: 4}  # easy start: early skills are shorter
DRILL = -1  # position of the hidden lesson holding listening/speaking practice exercises

# Exercise mix per difficulty stage (see PLAN.md §2).
STAGES = {
    0: ["pick", "pick", "pairs", "listen_word"],                                       # unit 1, lesson 1
    1: ["pick", "translate", "fill", "speak_word", "pairs"],                            # unit 1, lesson 2
    2: ["pick", "translate", "pairs", "fill", "speak", "listen_type"],                  # unit 2
    3: ["translate", "pairs", "translate_to", "fill", "listen_type", "speak", "type"],  # unit 3
}

RIVALS = [("Lucía", "#ff4b4b"), ("Mateo", "#ff9600"), ("Sofía", "#ce82ff"), ("Kenji", "#1cb0f6"),
          ("Amara", "#58cc02"), ("Liam", "#2b70c9"), ("Priya", "#ff86d0"), ("Noah", "#ffc800"),
          ("Chloé", "#00cd9c"), ("Omar", "#a560e8"), ("Elena", "#ff7878"), ("Yuki", "#4b4b4b")]

ARTICLES = {"el", "la", "los", "las", "un", "una", "le", "les", "une"}
_PUNCT = re.compile(r"^([¿¡«\"]*)(.*?)([.,!?;:»\"।]*)$")


def stage_of(unit_pos: int, lesson_pos: int) -> int:
    return min(lesson_pos, 1) if unit_pos == 1 else unit_pos


def _words(text: str) -> list[str]:
    # \u0900-\u0963 / \u0966-\u097F: Devanagari letters *and* vowel signs (which \w misses), minus the danda
    return re.findall(r"[\w'’\-\u0900-\u0963\u0966-\u097F]+", text)


@dataclass
class Item:
    """One word or sentence in a target language."""
    en: str
    text: str                                    # display form
    tiles: list[str]                             # word-bank tiles (no punctuation)
    alts: list[str] = field(default_factory=list)  # other accepted spellings: kana, romaji
    reading: str | None = None                   # shown under Japanese text
    emoji: str = ""


def word_item(lang: str, v) -> Item:
    en, emoji, es, fr, ja = v
    if lang == "hi":
        deva, roman = HINDI[en]
        return Item(en, deva, _words(deva), [roman], roman, emoji)
    if lang == "ja":
        kanji, kana, romaji = ja
        reading = romaji if kana == kanji else f"{kana} · {romaji}"
        return Item(en, kanji, [kanji], [a for a in (kana, romaji) if a != kanji], reading, emoji)
    text = es if lang == "es" else fr
    return Item(en, text, _words(text), [], None, emoji)


def sentence_item(lang: str, s) -> Item:
    en, es, fr, ja = s
    if lang == "hi":
        deva, roman = HINDI[en]
        return Item(en, deva, _words(deva), [roman], roman)
    if lang == "ja":
        kanji, kana, romaji = ja
        tokens = kanji.split()
        return Item(en, "".join(tokens), tokens, ["".join(kana.split()), romaji], f"{''.join(kana.split())} · {romaji}")
    text = es if lang == "es" else fr
    return Item(en, text, _words(text))


def build_hints(lang: str) -> dict[str, str]:
    """Word -> English, from every vocabulary list plus a function-word glossary."""
    hints = {k.lower(): v for k, v in GLOSSARY[lang].items()}
    for _, _, _, skills in COURSE:
        for _, _, vocab, _ in skills:
            for v in vocab:
                w, meaning = word_item(lang, v), v[0].removeprefix("the ")
                if lang == "ja":
                    hints[w.text] = meaning if not w.alts or w.alts[0] == w.text else f"{meaning} ({w.alts[0]})"
                    continue
                if lang == "hi":  # meaning + how to say it, for each word of the phrase
                    for part, roman in zip(w.text.split(), w.alts[0].split()):
                        hints.setdefault(part, f"{meaning} ({roman})")
                    continue
                hints[w.text.lower()] = v[0]  # whole phrase, e.g. "l'eau"
                parts = w.text.lower().split()
                if len(parts) == 2 and parts[0] in ARTICLES:
                    hints.setdefault(parts[1], meaning)
                else:
                    for p in parts:
                        hints.setdefault(p, v[0])
    return hints


def hinted(lang: str, item: Item, hints: dict[str, str]) -> list[dict]:
    """Display tokens with a translation hint where one is known.
    Punctuation becomes its own token so the client can attach it without a space."""
    def tok(t: str) -> dict:
        key = t.lower()
        h = hints.get(key) or (hints.get(key.split("'", 1)[1]) if "'" in key else None)
        return {"t": t, "h": h} if h else {"t": t}

    if lang == "ja":
        return [tok(t) for t in item.tiles]
    out = []
    for raw in item.text.split():
        lead, core, trail = _PUNCT.match(raw).groups()
        out += [{"t": lead}] if lead else []
        out += [tok(core)] if core else []
        out += [{"t": trail}] if trail else []
    return out


class LessonBuilder:
    """Builds the exercises of one lesson for one language, rotating through the skill's material."""

    def __init__(self, rng: random.Random, lang: str, words: list[Item], sentences: list[Item], hints: dict):
        self.rng, self.lang, self.words, self.sentences, self.hints = rng, lang, words, sentences, hints
        self.title = LANGUAGES[lang][0]
        self.en_pool = sorted({w for s in sentences for w in _words(s.en)})
        self.target_pool = sorted({t for s in sentences for t in s.tiles})

    def _distractors(self, pool: list[str], exclude: list[str], n: int = 3) -> list[str]:
        lowered = {e.lower() for e in exclude}
        candidates = [w for w in pool if w.lower() not in lowered]
        return self.rng.sample(candidates, min(n, len(candidates)))

    def _shuffled(self, items: list) -> list:
        items = list(items)
        self.rng.shuffle(items)
        return items

    def _answers(self, item: Item) -> list[str]:
        return [item.text, *item.alts]

    # ---- one method per exercise kind
    def pick(self, w: Item, new: bool) -> dict:
        others = self.rng.sample([x for x in self.words if x.text != w.text], 2)
        options = self._shuffled([{"text": x.text, "emoji": x.emoji, "reading": x.reading} for x in [w, *others]])
        return dict(type=T.multiple_choice, prompt=f'Which one of these is "{w.en}"?',
                    payload={"options": options, "new_word": new}, answers=[w.text], tts=None, reading=w.reading)

    def pairs(self, start: int) -> dict:
        chosen = (self.words[start:] + self.words[:start])[:5]
        return dict(type=T.match_pairs, prompt="Tap the matching pairs",
                    payload={"pairs": [[w.text, w.en] for w in chosen]}, answers=[], tts=None)

    def translate(self, s: Item) -> dict:
        tiles = self._shuffled(_words(s.en) + self._distractors(self.en_pool, _words(s.en)))
        return dict(type=T.translate, prompt="Translate this sentence",
                    payload={"tokens": hinted(self.lang, s, self.hints), "reading": s.reading, "words": tiles},
                    answers=[s.en, *ALTERNATES.get(s.en, [])], tts=s.text, reading=s.reading)

    def translate_to(self, s: Item) -> dict:
        tiles = self._shuffled(s.tiles + self._distractors(self.target_pool, s.tiles))
        return dict(type=T.translate, prompt=f"Write this in {self.title}",
                    payload={"sentence": s.en, "words": tiles, "target": True}, answers=self._answers(s), tts=None,
                    reading=s.reading)

    def fill(self, s: Item) -> dict:
        tokens = hinted(self.lang, s, self.hints)
        target = max(s.tiles, key=len)
        i = next(k for k, t in enumerate(tokens) if t["t"] == target)
        pool = [t for t in self.target_pool if len(t) > (1 if self.lang in SCRIPTS else 2)]
        options = self._shuffled([target, *self._distractors(pool, [target], 2)])
        return dict(type=T.fill_blank, prompt="Select the missing word",
                    payload={"before": tokens[:i], "after": tokens[i + 1:], "options": options, "translation": s.en},
                    answers=[target], tts=s.text, meaning=s.en, reading=s.reading)

    def listen_tap(self, item: Item) -> dict:
        pool = sorted({t for w in self.words for t in w.tiles}) if len(item.tiles) == 1 else self.target_pool
        tiles = self._shuffled(item.tiles + self._distractors(pool, item.tiles))
        return dict(type=T.listen_tap, prompt="Tap what you hear", payload={"words": tiles},
                    answers=self._answers(item), tts=item.text, meaning=item.en, reading=item.reading)

    def listen_type(self, item: Item) -> dict:
        hint = {"ja": "Type in hiragana, kanji or romaji", "hi": "Type in Hindi or romanized Hindi"}.get(
            self.lang, f"Type in {self.title}")
        return dict(type=T.listen_type, prompt="Type what you hear", payload={"placeholder": hint},
                    answers=self._answers(item), tts=item.text, meaning=item.en, reading=item.reading)

    def speak(self, item: Item) -> dict:
        kind = "word" if len(item.tiles) == 1 else "sentence"
        return dict(type=T.speak, prompt=f"Speak this {kind}",
                    payload={"tokens": hinted(self.lang, item, self.hints), "reading": item.reading, "translation": item.en},
                    answers=self._answers(item), tts=item.text, meaning=item.en, reading=item.reading)

    def type_answer(self, s: Item) -> dict:
        hint = {"ja": "Type in kana, kanji or romaji", "hi": "Type in Hindi or romanized Hindi"}.get(
            self.lang, f"Type in {self.title}")
        return dict(type=T.type_answer, prompt=f"Write this in {self.title}", payload={"text": s.en, "placeholder": hint},
                    answers=self._answers(s), tts=None, reading=s.reading)

    def lesson(self, lesson_no: int, stage: int) -> list[dict]:
        w = self.words[lesson_no * 2 % len(self.words):] + self.words[:lesson_no * 2 % len(self.words)]
        s = self.sentences[lesson_no % len(self.sentences):] + self.sentences[:lesson_no % len(self.sentences)]
        wi, si = iter(w), iter(s * 2)
        out = []
        for kind in STAGES[stage]:
            match kind:
                case "pick": out.append(self.pick(next(wi), new=stage == 0))
                case "pairs": out.append(self.pairs(lesson_no))
                case "listen_word": out.append(self.listen_tap(w[0]))
                case "speak_word": out.append(self.speak(w[1]))
                case "translate": out.append(self.translate(next(si)))
                case "translate_to": out.append(self.translate_to(next(si)))
                case "fill": out.append(self.fill(next(si)))
                case "speak": out.append(self.speak(next(si)))
                case "listen_type": out.append(self.listen_type(next(si)))
                case "type": out.append(self.type_answer(next(si)))
        return out

    def drill(self) -> list[dict]:
        """Listening + speaking practice pool for the Practice hub (never on the path)."""
        return ([self.listen_tap(s) for s in self.sentences] + [self.listen_type(w) for w in self.words[:3]]
                + [self.speak(s) for s in self.sentences] + [self.speak(w) for w in self.words[:3]])


def alphabet_lesson(rng: random.Random, lang: str, group: list[tuple[str, str, str]]) -> list[dict]:
    """Letters before words: pick the letter for a sound, match letters to sounds, then
    hear a kana (Japanese) or name a letter's sound (Spanish, French)."""
    def options(item, field, say=True):
        others = rng.sample([g for g in group if g != item], 2)
        opts = [{"text": g[field], "emoji": "", "say": g[2] if say else None} for g in [item, *others]]
        rng.shuffle(opts)
        return opts

    def pick(item, new):
        prompt = f'Which one is "{item[1]}"?' if lang in SCRIPTS else f'Which letter sounds like "{item[1]}"?'
        return dict(type=T.multiple_choice, prompt=prompt, payload={"options": options(item, 0), "new_word": new},
                    answers=[item[0]], tts=None)

    out = [pick(group[0], True), pick(group[1], True),
           dict(type=T.match_pairs, prompt="Tap the matching pairs",
                payload={"pairs": [[g[0], g[1]] for g in group]}, answers=[], tts=None)]
    char, sound, say = group[2]
    if lang in SCRIPTS:
        tiles = [char, *rng.sample([g[0] for g in group if g[0] != char], 3)]
        rng.shuffle(tiles)
        out.append(dict(type=T.listen_tap, prompt="Tap what you hear", payload={"words": tiles},
                        answers=[char, sound], tts=say, reading=sound))
    else:
        out.append(dict(type=T.multiple_choice, prompt=f'What sound does "{char}" make?',
                        payload={"options": options(group[2], 1, say=False)}, answers=[sound], tts=say))
    out.append(pick(group[3], False))
    return out


def seed_alphabet(db: Session, rng: random.Random, lang: str, unit: Unit) -> None:
    title, icon, groups = ALPHABET[lang]
    skill = Skill(unit=unit, position=1, title=title, icon=icon)
    db.add(skill)
    for l_pos, group in enumerate(groups):
        lesson = Lesson(skill=skill, position=l_pos)
        db.add(lesson)
        for e_pos, ex in enumerate(alphabet_lesson(rng, lang, group)):
            db.add(Exercise(lesson=lesson, position=e_pos, **ex))
    if lang in SCRIPTS:  # listening practice: hear each letter, pick it from its row
        drill = Lesson(skill=skill, position=DRILL)
        db.add(drill)
        for e_pos, (group, (char, sound, say)) in enumerate((grp, g) for grp in groups for g in grp):
            tiles = [char, *rng.sample([g[0] for g in group if g[0] != char], 3)]
            rng.shuffle(tiles)
            db.add(Exercise(lesson=drill, position=e_pos, type=T.listen_tap, prompt="Tap what you hear",
                            payload={"words": tiles}, answers=[char, sound], tts=say, reading=sound))
    db.flush()
    for char, sound, say in (g for group in groups for g in group):
        db.add(Phrase(skill_id=skill.id, kind="word", text=char, translation=sound,
                      reading=None if lang in SCRIPTS else f"as in {say}"))


def seed_content(db: Session) -> None:
    for lang, (title, flag, locale, spaced) in LANGUAGES.items():
        rng, hints = random.Random(lang), build_hints(lang)
        course = Course(language_code=lang, title=title, flag=flag, tts_locale=locale, word_spacing=spaced)
        db.add(course)
        for u_pos, (u_title, u_desc, color, skills) in enumerate(COURSE, 1):
            unit = Unit(course=course, position=u_pos, title=u_title, description=u_desc, color=color)
            if u_pos == 1:
                seed_alphabet(db, rng, lang, unit)  # letters first, then words
            for s_pos, (s_title, icon, vocab, sents) in enumerate(skills, 1 + (u_pos == 1)):
                skill = Skill(unit=unit, position=s_pos, title=s_title, icon=icon)
                words = [word_item(lang, v) for v in vocab]
                sentences = [sentence_item(lang, x) for x in sents]
                builder = LessonBuilder(rng, lang, words, sentences, hints)
                lessons = [(n, builder.lesson(n, stage_of(u_pos, n))) for n in range(LESSONS_PER_UNIT[u_pos])]
                for l_pos, exercises in [*lessons, (DRILL, builder.drill())]:
                    lesson = Lesson(skill=skill, position=l_pos)
                    db.add(lesson)
                    for e_pos, ex in enumerate(exercises):
                        db.add(Exercise(lesson=lesson, position=e_pos, **ex))
                db.flush()
                for it, kind in [*((w, "word") for w in words), *((x, "sentence") for x in sentences)]:
                    db.add(Phrase(skill_id=skill.id, kind=kind, text=it.text, translation=it.en,
                                  reading=it.reading, emoji=it.emoji or None))
    for d in achievements.DEFINITIONS:
        db.add(Achievement(code=d.code, title=d.title, description=d.description, icon=d.icon, color=d.color))
    db.flush()


def new_user(db: Session, username: str, now: datetime, **kw) -> User:
    """A fresh learner on the first course (the welcome page lets them pick another)."""
    fields = dict(display_name="New learner", hearts_updated_at=now, created_at=now,
                  league_week=week_bounds(now)[0].date(), course_id=db.scalar(select(Course.id).order_by(Course.id)))
    user = User(username=username, **fields | {k: v for k, v in kw.items() if v is not None})
    db.add(user)
    db.flush()
    return user


def _completed_session(db: Session, user: User, lesson: Lesson, when: datetime, xp: int) -> None:
    s = LessonSession(user_id=user.id, skill_id=lesson.skill_id, lesson_id=lesson.id, mode=SessionMode.lesson,
                      status=SessionStatus.completed, exercise_ids=[e.id for e in lesson.exercises],
                      mistakes=0 if xp > settings.lesson_xp else 1,
                      started_at=when - timedelta(minutes=3), completed_at=when, result={})
    db.add(s)
    db.flush()
    db.add(XpEvent(user_id=user.id, session_id=s.id, amount=xp, source="lesson", local_date=when.date(),
                   created_at=when))
    user.xp_total += xp


def seed_demo_user(db: Session, now: datetime) -> User:
    """A Spanish learner mid-way through unit 1 with a live streak, so every screen has data."""
    course = db.scalar(select(Course).where(Course.language_code == "es"))
    user = new_user(db, settings.default_username, now, display_name="Demo Learner", avatar_color="#1cb0f6",
                    course_id=course.id, gems=650, hearts=4, hearts_updated_at=now - timedelta(minutes=10),
                    streak=4, longest_streak=6, streak_freezes=1, daily_goal_xp=20, onboarded=True,
                    created_at=now - timedelta(days=21))
    skills = [s for u in course.units for s in u.skills]
    # Finished the letters, Basics and Greetings, and the first lesson of Café, over the last 4 days (the streak).
    done = [(skills[0], len(skills[0].lessons)), (skills[1], 2), (skills[2], 2), (skills[3], 1)]
    lessons = [lesson for skill, n in done for lesson in skill.lessons[:n]]
    for i, lesson in enumerate(lessons):
        day = now - timedelta(days=4 - i * 4 // len(lessons))
        _completed_session(db, user, lesson, day.replace(hour=18, minute=i), 10 + (5 if i % 2 else 0))
    for skill, n in done:
        db.add(UserSkillProgress(user_id=user.id, skill_id=skill.id, lessons_completed=n, legendary=False,
                                 updated_at=now))
    user.last_active_date = (now - timedelta(days=1)).date()  # yesterday: today's lesson extends the streak
    user.perfect_lessons = 3
    db.flush()
    achievements.evaluate(db, user, now)
    return user


def seed_if_empty(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Course)):
        return
    now = clock.now()
    seed_content(db)
    for name, color in RIVALS:
        new_user(db, name.lower(), now, display_name=name, avatar_color=color, is_bot=True, onboarded=True,
                 xp_total=random.Random(name).randint(300, 4000))
    seed_demo_user(db, now)
    db.commit()
    top_up_rivals(db, now)


def reset_user(db: Session, user: User, now: datetime) -> User:
    """Wipe a learner's progress (POST /api/dev/reset). The demo learner is re-seeded
    with its sample progress; anyone else starts over, keeping their login."""
    keep = {"username": user.username, "password_hash": user.password_hash, "google_sub": user.google_sub,
            "email": user.email, "display_name": user.display_name,
            "avatar_color": user.avatar_color, "timezone": user.timezone, "course_id": user.course_id}
    tokens = [t for t, in db.execute(select(AuthSession.token_hash).where(AuthSession.user_id == user.id))]
    session_ids = select(LessonSession.id).where(LessonSession.user_id == user.id)
    db.execute(delete(XpEvent).where(XpEvent.user_id == user.id))
    db.execute(delete(SessionAnswer).where(SessionAnswer.session_id.in_(session_ids)))
    for model in (LessonSession, UserAchievement, UserSkillProgress, QuestClaim, AuthSession):
        db.execute(delete(model).where(model.user_id == user.id))
    db.delete(user)
    db.flush()
    if keep["username"] == settings.default_username:
        fresh = seed_demo_user(db, now)
    else:
        fresh = new_user(db, keep.pop("username"), now, **keep)
    db.add_all(AuthSession(token_hash=t, user_id=fresh.id, created_at=now) for t in tokens)  # stay signed in
    db.commit()
    return fresh


if __name__ == "__main__":
    from .db import SessionLocal, rebuild

    rebuild()
    with SessionLocal() as session:
        seed_if_empty(session)
    print("Database seeded.")
