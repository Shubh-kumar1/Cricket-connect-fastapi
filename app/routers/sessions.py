from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_provider
from app.models.user import User
from app.schemas.session import SessionCreate, SessionRead, SessionSearchResult
from app.services.providers import get_profile
from app.services.sessions import (
    create_session,
    delete_session,
    list_provider_sessions,
    search_sessions,
    update_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create(data: SessionCreate, db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    return create_session(db, get_profile(db, provider_user.provider_profile.id), data)


@router.get("/search", response_model=list[SessionSearchResult])
def search(
    sport: str | None = None,
    city: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return [
        SessionSearchResult.model_validate(
            {
                **session.__dict__,
                "sport_name": sport_name,
                "provider_name": provider_name,
                "venue_city": venue_city,
            }
        )
        for session, sport_name, provider_name, venue_city in search_sessions(db, sport, city)
    ]


@router.get("/mine", response_model=list[SessionRead])
def list_mine(db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    return list_provider_sessions(db, get_profile(db, provider_user.provider_profile.id))


@router.put("/{session_id}", response_model=SessionRead)
def update(
    session_id: int,
    data: SessionCreate,
    db: Session = Depends(get_db),
    provider_user: User = Depends(require_provider),
):
    return update_session(db, get_profile(db, provider_user.provider_profile.id), session_id, data)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(session_id: int, db: Session = Depends(get_db), provider_user: User = Depends(require_provider)):
    delete_session(db, get_profile(db, provider_user.provider_profile.id), session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

