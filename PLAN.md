# Phase 2 Plan: Languages, Easy Start, Listening & Speaking

**Status: implemented.** **Decisions:** Spanish + French + Japanese · beginner protection **on** (first 2 lessons of a course cost no hearts) · build everything, including section 4.

Status legend: ⬜ todo · 🔨 in progress · ✅ done

---

## 1. Three languages: 🇪🇸 Spanish, 🇫🇷 French, 🇯🇵 Japanese

| # | Change | Where | Status |
|---|---|---|---|
| 1.1 | Write content once per topic (9 skills × 6 words + 5 sentences) with translations for every language | `backend/app/content.py` | ✅ |
| 1.2 | Japanese: sentences stored as tokens (no spaces in Japanese). Learners may answer in **kanji/kana, hiragana or romaji** | `content.py`, `grading.py` | ✅ |
| 1.3 | Seed one course per language from the same topics | `seed.py` | ✅ |
| 1.4 | `courses.tts_locale` (`es-ES` / `fr-FR` / `ja-JP`) and `word_spacing`, sent to the client | `models.py`, `/api/me` | ✅ |
| 1.5 | `GET /api/courses` (progress per course) and `PATCH /api/me {course_id}` to switch | `routers/course.py`, `routers/me.py` | ✅ |
| 1.6 | Progress stays per skill, so each course keeps its own path. XP, streak, hearts and gems are shared, as on Duolingo | no change | ✅ |
| 1.7 | Clicking the flag in the top bar opens a course switcher; Settings → Courses becomes real | `Shell.tsx`, Settings | ✅ |
| 1.8 | Remove hardcoded "Spanish" text and `es-ES` audio; use the course's name and locale | seed generator, widgets, `sound.ts` | ✅ |
| 1.9 | Onboarding `/welcome`: pick a language, pick a daily goal (Casual by default), then start lesson 1 | new page, `users.onboarded` | ✅ |

## 2. Easy start (difficulty ramp)

Exercise mix and lesson length grow with position on the path:

| Stage | Exercises | Types | Extra help |
|---|---|---|---|
| Unit 1, lesson 1 | 4 | "New word" picture cards, match pairs, tap what you hear | Hints, no typing |
| Unit 1, lesson 2 | 5 | + translation (word bank), fill in the blank, speak one word | Hints |
| Unit 2 | 6 | + speak a sentence, type what you hear | Hints |
| Unit 3 | 7 | + free typing, translation in both directions | Hints |

| # | Change | Status |
|---|---|---|
| 2.1 | Shorter early skills: Unit 1 = 2 lessons per skill, Unit 2 = 3, Unit 3 = 4 | ✅ |
| 2.2 | Generator takes a difficulty stage → exercise count and types per the table above | ✅ |
| 2.3 | **Word hints:** tap/hover any word in a target-language sentence to see its translation (built from the vocabulary lists plus a small function-word glossary) | ✅ |
| 2.4 | **Typo tolerance:** one letter off (edit distance 1) still counts, with a "Watch out for typos" note | ✅ |
| 2.5 | **Beginner protection:** the first 2 lessons of every course never cost hearts | ✅ |
| 2.6 | New learners default to the Casual goal (10 XP), so day one hits the goal | ✅ |

## 3. Listening & speaking

| # | Change | Status |
|---|---|---|
| 3.1 | `listen_tap`: hear audio, build the sentence from tiles; 🐢 slow replay | ✅ |
| 3.2 | `listen_type`: hear audio, type it (Japanese accepts kana or romaji) | ✅ |
| 3.3 | `speak`: read aloud. The browser's speech recognition produces a transcript and the **server** grades it with a forgiving similarity match (≥ 75%) | ✅ |
| 3.4 | "Can't listen now" / "Can't speak now": skip those exercise types for 15 minutes with no heart loss. The server accepts the skip only for listening/speaking types | ✅ |
| 3.5 | Browsers without speech recognition (Firefox) fall back automatically to the skip | ✅ |
| 3.6 | Practice hub: real **Listening** and **Speaking** practice (8 exercises each) | ✅ |
| 3.7 | Audio everywhere: speaker button on target-language text, playback speed setting, warning when the system has no voice for the language | ✅ |

## 4. Extras

| # | Feature | Design | Status |
|---|---|---|---|
| 4.1 | **Mistakes review** | Practice built from the most recently missed questions (stored answers) | ✅ |
| 4.2 | **Guidebook** | `phrases` table (key words and sentences per skill) → `GET /api/units/{id}/guidebook`, modal with audio | ✅ |
| 4.3 | **Daily quests + chests** | Earn goal XP · complete 2 lessons · 1 perfect lesson. `GET /api/quests`, `POST /api/quests/{code}/claim` (idempotent via unique `quest_claims` row) | ✅ |
| 4.4 | **Streak calendar** | Practiced days from the XP ledger, shown on the profile | ✅ |
| 4.5 | **League promotion** | `users.league_tier` + `league_week`. At week rollover (settled on read): top 7 promote, bottom 5 demote, celebration modal | ✅ |
| 4.6 | **Browser end-to-end tests** (Playwright) | Fresh learner → onboarding → Japanese lesson 1, driven only through the UI | ✅ |

## Schema changes

- `courses` + `tts_locale`, `word_spacing`
- `exercises.type` + `listen_tap`, `listen_type`, `speak`
- `phrases` (new): `skill_id`, `kind` (word/sentence), `text`, `translation`, `reading`, `emoji`
- `users` + `onboarded`, `league_tier`, `league_week`
- `quest_claims` (new): `(user_id, day, code)` primary key
- No Alembic: a schema-version number (`PRAGMA user_version`) rebuilds the demo database when the schema changes

## Testing

- **pytest:** per-language seeding, difficulty ramp, Japanese kana/romaji grading, typo tolerance, speaking similarity, skip rules, course switching, beginner protection, quests (claim once), league promotion, mistakes practice
- **Playwright:** onboarding and a full lesson through the real UI
- **Manual browser pass:** all three languages, mobile and dark mode

## 6. Letters first, clearer audio ✅

- Every course opens with a letters skill before Basics: **Hiragana** (あ, か, さ rows) for Japanese, tricky letters and sounds for Spanish (ñ, ll, j, rr…) and French (é, ç, ou, on…), each sound heard through an example word. Letters + Basics are the free warm-up skills.
- After every answer the feedback bar shows **how to say it** (kana · romaji / letter sound) and the **English meaning**; speaking exercises show the meaning up front.
- TTS picks the clearest installed voice (Chrome's Google voices, then macOS Premium/Enhanced) and avoids the robotic Eloquence voices. Settings shows the voice in use and has a Test button.

## 5. Multi-user ✅

Every browser gets its own guest learner on first visit (HttpOnly session cookie; only the token's SHA-256 is stored in `auth_sessions`). A guest can register a username + password (stdlib `scrypt`) to keep progress and sign in on other devices. Leagues rank real learners in the same tier plus the seeded bots. **Google sign-in** (Google Identity Services ID token, verified server-side) links a guest's progress or signs in; enabled by `GOOGLE_CLIENT_ID`. `/api/dev/demo` signs in as the sample learner.

## Not doing (low value for the effort)

Chess (off the brief's language-learning scope), stories, avatar builder, push notifications, real payments, email verification / password reset, login rate limiting.
