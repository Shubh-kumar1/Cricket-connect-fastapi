from pydantic import BaseModel, ConfigDict, Field


class VenueCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    address: str = Field(min_length=2, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    latitude: float | None = None
    longitude: float | None = None


class VenueRead(VenueCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_id: int

