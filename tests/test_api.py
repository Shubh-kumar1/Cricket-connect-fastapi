from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User, UserRole
from app.routers import venues


def test_health_check():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_authenticated_player_can_browse_venues(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: User(id=1, role=UserRole.PLAYER, is_active=True)
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(venues, "list_venues", lambda _: [])

    try:
        response = TestClient(app).get("/api/v1/venues")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []


def test_venue_browse_requires_authentication():
    response = TestClient(app).get("/api/v1/venues")

    assert response.status_code == 401
