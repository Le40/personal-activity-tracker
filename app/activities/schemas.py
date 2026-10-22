from datetime import datetime
from typing import Self
from pydantic import AwareDatetime, model_validator
from app.activities.options import ActivityType, EaseRating, EASE_RATING_ACTIVITY_TYPES

from pydantic import BaseModel, ConfigDict, Field


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    activity_type: ActivityType
    started_at: datetime
    ended_at: datetime | None
    notes: str | None
    ease_rating: EaseRating | None

class ActivityInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=30)
    activity_type: ActivityType
    notes: str | None = None
    ease_rating: EaseRating | None = None

    @model_validator(mode="after")
    def validate_ease_rating(self) -> Self:
        if (
            self.ease_rating is not None
            and self.activity_type not in EASE_RATING_ACTIVITY_TYPES
        ):
            raise ValueError("Ease rating is not supported for this activity type")
        return self

class CompletedActivityInput(ActivityInput):
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.ended_at <= self.started_at:
            raise ValueError("End time must be after start time")
        return self

class ActivityUpdate(ActivityInput):
    started_at: AwareDatetime | None = None
    ended_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if (self.started_at is None) != (self.ended_at is None):
            raise ValueError("Both timestamps must be provided together")

        if self.started_at is not None:
            if self.ended_at <= self.started_at:
                raise ValueError("End time must be after start time")

        return self