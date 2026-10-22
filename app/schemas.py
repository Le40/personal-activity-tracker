from datetime import datetime
from typing import Self
from pydantic import model_validator
from app.options import ActivityType, EaseRating, EASE_RATING_ACTIVITY_TYPES

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
            raise ValueError("Ease rating is only allowed for work activities")
        return self