"""Request bodies, validated at the trust boundary by Pydantic."""
from typing import Any, Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, field_validator

from .config import settings
from .models import SessionMode


class StartSession(BaseModel):
    skill_id: int | None = None
    mode: SessionMode = SessionMode.lesson
    # practice only: a mix of finished lessons, listening/speaking drills, or recent mistakes
    kind: Literal["mix", "listening", "speaking", "mistakes"] = "mix"


class SubmitAnswer(BaseModel):
    exercise_id: int
    # str for choice/text exercises, list of [left, right] pairs for match_pairs
    value: str | list[list[str]] = Field("", description="The learner's answer")
    skip: bool = False  # "Can't listen / speak now": allowed for listening and speaking exercises only

    @field_validator("value")
    @classmethod
    def _bounded(cls, v: Any):
        if isinstance(v, str) and len(v) > 300:
            raise ValueError("answer too long")
        if isinstance(v, list) and (len(v) > 10 or any(len(p) != 2 for p in v)):
            raise ValueError("pairs must be a short list of [left, right]")
        return v


class UpdateSettings(BaseModel):
    daily_goal_xp: int | None = None
    display_name: str | None = Field(None, min_length=1, max_length=60)
    timezone: str | None = None
    course_id: int | None = None
    onboarded: bool | None = None

    @field_validator("daily_goal_xp")
    @classmethod
    def _goal(cls, v):
        if v is not None and v not in settings.daily_goal_options:
            raise ValueError(f"daily goal must be one of {settings.daily_goal_options}")
        return v

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v):
        if v is not None and v not in available_timezones():
            raise ValueError("unknown timezone")
        return v


class TimeTravel(BaseModel):
    days: float = Field(1, ge=-30, le=30)


class Credentials(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class GoogleCredential(BaseModel):
    credential: str = Field(..., min_length=20, max_length=4096)  # ID token from Google Identity Services
