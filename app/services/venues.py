from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider import ProviderProfile
from app.models.venue import Venue
from app.schemas.venue import VenueCreate


def create_venue(db: Session, provider: ProviderProfile, data: VenueCreate) -> Venue:
    venue = Venue(provider_id=provider.id, **data.model_dump())
    db.add(venue)
    db.commit()
    db.refresh(venue)
    return venue


def list_provider_venues(db: Session, provider: ProviderProfile) -> list[Venue]:
    return list(db.scalars(select(Venue).where(Venue.provider_id == provider.id).order_by(Venue.id)))


def list_venues(db: Session) -> list[Venue]:
    return list(db.scalars(select(Venue).order_by(Venue.id)))


def update_venue(db: Session, provider: ProviderProfile, venue_id: int, data: VenueCreate) -> Venue:
    venue = db.scalar(select(Venue).where(Venue.id == venue_id, Venue.provider_id == provider.id))
    if venue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    for key, value in data.model_dump().items():
        setattr(venue, key, value)
    db.commit()
    db.refresh(venue)
    return venue


def delete_venue(db: Session, provider: ProviderProfile, venue_id: int) -> None:
    venue = db.scalar(select(Venue).where(Venue.id == venue_id, Venue.provider_id == provider.id))
    if venue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venue not found")
    db.delete(venue)
    db.commit()
