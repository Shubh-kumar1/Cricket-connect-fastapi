from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    venue_id: int
    sport_id: int
    title: str = Field(min_length=2, max_length=150)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(gt=0, le=10000)


class SessionRead(SessionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int


class SessionSearchResult(SessionRead):
    sport_name: str
    provider_name: str
    venue_city: str

