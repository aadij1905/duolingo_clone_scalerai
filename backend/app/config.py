"""Runtime configuration.

Every tunable game constant lives here so the economy can be adjusted from one
place (or from env vars in production) without touching business logic.
"""
import os
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "duolingo.db"  # backend/duolingo.db, whatever the cwd


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{_DEFAULT_DB}")
    # Comma-separated list of allowed browser origins (the Next.js app).
    cors_origins: tuple[str, ...] = tuple(
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
    )
    # The seeded sample learner (sign in to it from the welcome page while dev routes are on).
    default_username: str = os.getenv("DEFAULT_USERNAME", "demo")
    # OAuth client ID from Google Cloud Console; "Sign in with Google" is hidden when unset.
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    # No migrations: when the schema version changes, wipe and re-seed the SQLite file. Fine locally;
    # set to 0 in production so a deploy refuses to start instead of deleting every account.
    reset_db_on_schema_change: bool = os.getenv("RESET_DB_ON_SCHEMA_CHANGE", "1") == "1"
    # Send the session cookie over HTTPS only. Turn on in production.
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "0") == "1"
    # Exposes /api/dev/* (time travel, reset). On by default because the brief
    # asks for streak/day logic to be testable on the hosted demo.
    enable_dev_routes: bool = os.getenv("ENABLE_DEV_ROUTES", "1") == "1"

    # --- game economy ---
    max_hearts: int = 5
    heart_regen_minutes: int = int(os.getenv("HEART_REGEN_MINUTES", "30"))
    heart_refill_gem_cost: int = 350
    streak_freeze_gem_cost: int = 200
    max_streak_freezes: int = 2  # Duolingo lets learners equip two at a time
    lesson_xp: int = 10
    perfect_lesson_bonus_xp: int = 5
    practice_xp: int = 10
    legendary_xp: int = 40
    lesson_gems: int = 5
    daily_goal_gems: int = 20
    legendary_time_limit_s: int = 150
    legendary_max_mistakes: int = 3
    beginner_free_skills: int = 2  # letters + Basics: the first skills of every course never cost hearts
    speak_min_similarity: float = 0.75
    daily_goal_options: tuple[int, ...] = (10, 20, 30, 50)


settings = Settings()
