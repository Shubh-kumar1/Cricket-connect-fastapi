from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.booking import BookingStatus


class BookingCreate(BaseModel):
    session_id: int


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    player_id: int
    status: BookingStatus
    created_at: datetime


class BookingStatusUpdate(BaseModel):
    status: BookingStatus

