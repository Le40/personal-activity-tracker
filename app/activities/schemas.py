from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.activities.options import EASE_RATING_ACTIVITY_TYPES, ActivityType, EaseRating


def validate_not_future(value: datetime) -> datetime:
    if value > datetime.now(UTC):
        raise ValueError("Timestamp cannot be in the future")

    return value

PastDatetime = Annotated[
    AwareDatetime,
    AfterValidator(validate_not_future),
]


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id              : int
    name            : str | None
    activity_type   : ActivityType
    started_at      : datetime
    ended_at        : datetime | None
    notes           : str | None
    ease_rating     : EaseRating | None

class ActivityInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name            : str | None = Field(default=None, min_length=1, max_length=30)
    activity_type   : ActivityType
    notes           : str | None = None
    ease_rating     : EaseRating | None = None

    @field_validator("name", "notes", mode="before")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_ease_rating(self) -> Self:
        if (
            self.ease_rating is not None
            and self.activity_type not in EASE_RATING_ACTIVITY_TYPES
        ):
            raise ValueError("Ease rating is not supported for this activity type")
        return self

class CompletedActivityInput(ActivityInput):
    started_at: PastDatetime
    ended_at:   PastDatetime

    @model_validator(mode="after")
    def validate_time_range(self) -> Self:
        if self.ended_at <= self.started_at:
            raise ValueError("End time must be after start time")
        return self

class ActivityUpdate(ActivityInput):
    started_at: PastDatetime | None = None
    ended_at:   PastDatetime | None = None

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if (self.started_at is None) != (self.ended_at is None):
            raise ValueError("Both timestamps must be provided together")

        if (self.started_at is not None
            and self.ended_at <= self.started_at):
                raise ValueError("End time must be after start time")

        return self