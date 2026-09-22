from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Venue(Base):
    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    latitude: Mapped[Optional[float]]
    longitude: Mapped[Optional[float]]

    provider: Mapped["ProviderProfile"] = relationship(back_populates="venues")
    sessions: Mapped[list["SessionModel"]] = relationship(back_populates="venue")
