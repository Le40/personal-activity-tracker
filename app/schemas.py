from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ActivitySessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    activity_type: str
    started_at: datetime
    ended_at: datetime | None
    notes: str | None

class ActivitySessionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=30)
    activity_type: Literal['work', 'exercise', 'meal', 'break', 'other']
    notes: str | None = None