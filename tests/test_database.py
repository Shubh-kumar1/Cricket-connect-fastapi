import pytest

from app.database import normalize_database_url


@pytest.mark.parametrize(
    ("database_url", "expected_url"),
    [
        (
            "postgres://user:pass@db.example:5432/cricket?sslmode=require",
            "postgresql+psycopg://user:pass@db.example:5432/cricket?sslmode=require",
        ),
        (
            "postgresql://user:pass@db.example:5432/cricket?sslmode=require",
            "postgresql+psycopg://user:pass@db.example:5432/cricket?sslmode=require",
        ),
        (
            "postgresql+psycopg://user:pass@db.example:5432/cricket?sslmode=require",
            "postgresql+psycopg://user:pass@db.example:5432/cricket?sslmode=require",
        ),
        ("sqlite:///test.db", "sqlite:///test.db"),
    ],
)
def test_normalize_database_url_preserves_url_components(database_url, expected_url):
    assert normalize_database_url(database_url) == expected_url
