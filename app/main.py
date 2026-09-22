from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.database import Base, engine
from app.routers import auth, bookings, providers, sessions, venues


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Schema creation is owned by Alembic in deployed environments.
    yield


app = FastAPI(title="Cricket Connect API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5179",
        "http://localhost:5180",
        "https://cricket-connect-fastapi.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(venues.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")


@app.exception_handler(OperationalError)
async def database_unavailable(_: object, __: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Database is temporarily unavailable"},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
