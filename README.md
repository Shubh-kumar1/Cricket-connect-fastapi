# Cricket Connect Backend - Phase 0

FastAPI backend for connecting players with provider-created cricket and sports sessions. Phase 0 uses a modular Router -> Service -> SQLAlchemy/Database architecture.

## Requirements

- Python 3.11+
- PostgreSQL 14+

## Setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Create the database:

```powershell
psql -U postgres
CREATE DATABASE cricket_connect;
\q
```

Set `DATABASE_URL` and `JWT_SECRET_KEY` in `.env`.

## Migrations and seed data

```powershell
alembic upgrade head
python -m scripts.seed
```

The migration seeds Cricket, Football, Badminton, and Tennis. The seed command is idempotent and can be run again safely.

## Run the API

```powershell
uvicorn app.main:app --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Tests

```powershell
pytest
```

`tests/test_booking_concurrency.py` is an integration test and runs when `DATABASE_URL` points to PostgreSQL. It starts concurrent transactions against a capacity-one session and verifies only one active booking succeeds. The health and password tests run without a database connection.

## Database relationships

- `users` has one optional `provider_profiles` row and can own many `bookings`.
- `provider_profiles` belongs to one provider user and owns many `venues` and `sessions`.
- `sports` is a shared lookup table referenced by `sessions`.
- `venues` belongs to a provider and can host many sessions.
- `sessions` belongs to one provider, venue, and sport and has many bookings.
- `bookings` links a player to a session and has a unique `(session_id, player_id)` constraint.

## API endpoints

| Method | Endpoint | Access |
|---|---|---|
| GET | `/health` | Public |
| POST | `/api/v1/auth/register` | Public |
| POST | `/api/v1/auth/login` | Public |
| POST/GET/DELETE | `/api/v1/providers/me/profile`, `/api/v1/providers/{provider_id}/profile` | Provider / authenticated |
| GET | `/api/v1/venues` | Authenticated |
| POST | `/api/v1/venues` | Provider |
| GET | `/api/v1/venues/mine` | Provider |
| PUT/DELETE | `/api/v1/venues/{venue_id}` | Provider |
| POST/GET/PUT/DELETE | `/api/v1/sessions`, `/api/v1/sessions/mine`, `/api/v1/sessions/{session_id}` | Provider |
| GET | `/api/v1/sessions/search?sport=Cricket&city=Delhi` | Authenticated |
| POST/GET | `/api/v1/bookings`, `/api/v1/bookings/mine` | Player |
| GET/PATCH | `/api/v1/bookings/provider`, `/api/v1/bookings/{booking_id}` | Provider |

## Authentication

Register, then log in with email and password. Login returns a JWT bearer token. Send it as:

```text
Authorization: Bearer <access_token>
```

The token contains the user id and role. Dependencies load the user from PostgreSQL and enforce `PLAYER` or `PROVIDER` access at the router boundary.

## Example requests

Register a provider:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"provider@example.com","full_name":"A Provider","password":"password123","role":"PROVIDER"}'
```

Login:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"provider@example.com","password":"password123"}'
```

Create a provider profile:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/providers/me/profile `
  -H "Authorization: Bearer <provider-token>" -H "Content-Type: application/json" `
  -d '{"business_name":"Delhi Cricket Academy","bio":"Weekend cricket sessions","phone":"9999999999"}'
```

Create a booking as a player:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/bookings `
  -H "Authorization: Bearer <player-token>" -H "Content-Type: application/json" `
  -d '{"session_id":1}'
```

## Concurrency decision

Booking creation begins a database transaction and selects the target session with PostgreSQL `SELECT ... FOR UPDATE` through SQLAlchemy's `with_for_update()`. This serializes all capacity decisions for that session. The locked transaction counts active `PENDING` and `CONFIRMED` bookings and inserts only when the count is below capacity. The player/session unique constraint also prevents duplicate active booking records.

This is deliberately not an application-only capacity check. PostgreSQL is the source of truth for concurrent requests.

## Decisions and limitations

- Provider registration is self-service; a provider must create a profile before creating venues or sessions.
- Search uses case-insensitive exact matching for sport and city and is intentionally simple for Phase 0.
- Booking statuses remain exactly `PENDING`, `CONFIRMED`, and `CANCELLED`.
- The requested provider "mark completed" action is not implemented because the finalized Phase 0 status enum has no completion state. A completion-state representation (new enum value versus separate completion field) must be decided before adding that action.
- No cancellation endpoint is included yet; provider booking status management can set `CANCELLED`, while player cancellation policy is deferred.
- Redis, WebSockets, chat, payments, matchmaking, Elasticsearch, ML, frontend, per-sport tables, and EAV are intentionally excluded.
