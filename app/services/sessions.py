from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provider import ProviderProfile
from app.models.session import SessionModel
from app.models.sport import Sport
from app.models.venue import Venue
from app.schemas.session import SessionCreate


def create_session(db: Session, provider: ProviderProfile, data: SessionCreate) -> SessionModel:
    venue = db.scalar(select(Venue).where(Venue.id == data.venue_id, Venue.provider_id == provider.id))
    if venue is None:
        raise HTTPException(status_code=400, detail="Venue does not belong to provider")
    if db.get(Sport, data.sport_id) is None:
        raise HTTPException(status_code=400, detail="Sport not found")
    if data.ends_at <= data.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    session = SessionModel(provider_id=provider.id, **data.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_provider_sessions(db: Session, provider: ProviderProfile) -> list[SessionModel]:
    return list(db.scalars(select(SessionModel).where(SessionModel.provider_id == provider.id).order_by(SessionModel.starts_at)))


def update_session(db: Session, provider: ProviderProfile, session_id: int, data: SessionCreate) -> SessionModel:
    session = db.scalar(select(SessionModel).where(SessionModel.id == session_id, SessionModel.provider_id == provider.id))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    venue = db.scalar(select(Venue).where(Venue.id == data.venue_id, Venue.provider_id == provider.id))
    if venue is None or db.get(Sport, data.sport_id) is None:
        raise HTTPException(status_code=400, detail="Invalid venue or sport")
    if data.ends_at <= data.starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    for key, value in data.model_dump().items():
        setattr(session, key, value)
    db.commit()
    db.refresh(session)
    return session


def delete_session(db: Session, provider: ProviderProfile, session_id: int) -> None:
    session = db.scalar(select(SessionModel).where(SessionModel.id == session_id, SessionModel.provider_id == provider.id))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    db.delete(session)
    db.commit()


def search_sessions(db: Session, sport: str | None, city: str | None) -> list[tuple[SessionModel, str, str, str]]:
    query = (
        select(SessionModel, Sport.name, ProviderProfile.business_name, Venue.city)
        .join(Sport, SessionModel.sport_id == Sport.id)
        .join(ProviderProfile, SessionModel.provider_id == ProviderProfile.id)
        .join(Venue, SessionModel.venue_id == Venue.id)
    )
    if sport:
        query = query.where(Sport.name.ilike(sport))
    if city:
        query = query.where(Venue.city.ilike(city))
    return list(db.execute(query.order_by(SessionModel.starts_at)).all())

