from sqlalchemy import select

from app.database import SessionLocal
from app.models.sport import Sport


SPORTS = ("Cricket", "Football", "Badminton", "Tennis")


def seed_sports() -> None:
    with SessionLocal.begin() as db:
        existing = set(db.scalars(select(Sport.name)))
        for name in SPORTS:
            if name not in existing:
                db.add(Sport(name=name))


if __name__ == "__main__":
    seed_sports()
    print("Sports seed complete.")

