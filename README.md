# Contacts API

A production-ready REST API for managing contacts built with FastAPI, SQLAlchemy 2.0, and Pydantic v2.

## Features

- **CRUD Operations**: Create, read, update (full/partial), and delete contacts
- **Search**: Case-insensitive search by first name, last name, or email
  - `q` parameter: OR semantics across all three fields
  - Individual field parameters: AND semantics when combined
- **Upcoming Birthdays**: Find contacts with birthdays in the next N days (default: 7, range: 1-365)
- **Pagination**: Configurable limit (1-100, default: 20) and offset
- **Validation**: Strict input validation with Pydantic v2
  - Email validation via `EmailStr`
  - Phone validation via regex: `^\+?[0-9()\-.\s]{7,20}$`
- **Error Handling**: 409 Conflict for duplicate emails, 404 Not Found for missing resources
- **API Documentation**: Interactive Swagger UI (`/docs`) and ReDoc (`/redoc`)

## Tech Stack

- **Python** 3.11+
- **FastAPI** - Modern web framework
- **SQLAlchemy 2.0** - ORM with declarative style
- **Pydantic v2** - Data validation
- **PostgreSQL** - Database
- **Alembic** - Database migrations
- **Poetry** - Dependency management
- **Docker** - Containerization

## Quick Start

### Option 1: Docker (Recommended)

1. **Clone and navigate to the project:**
   ```bash
   cd goit-pythonweb-hw-08
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Start services (migrations run automatically):**
   ```bash
   docker-compose up -d
   ```

4. **Access the API:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health

### Option 2: Local Development

1. **Prerequisites:**
   - Python 3.11+
   - PostgreSQL 15+
   - Poetry

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Create and configure `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Create PostgreSQL database:**
   ```bash
   createdb contacts_db
   # Or with Docker:
   docker run -d --name postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=contacts_db -p 5432:5432 postgres:15-alpine
   ```

5. **Run migrations:**
   ```bash
   poetry run alembic upgrade head
   ```

6. **Start the server:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

7. **Access the API:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

Base prefix: `/api`

### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/contacts` | Create a new contact (409 if email exists) |
| GET | `/api/contacts` | List contacts with filters and pagination |
| GET | `/api/contacts/{id}` | Get contact by ID (404 if not found) |
| PUT | `/api/contacts/{id}` | Full update contact (all fields required) |
| PATCH | `/api/contacts/{id}` | Partial update contact (only provided fields) |
| DELETE | `/api/contacts/{id}` | Delete contact (404 if not found) |
| GET | `/api/contacts/upcoming-birthdays` | Get contacts with upcoming birthdays |

### Query Parameters for List Endpoint

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | None | General search (OR across first_name, last_name, email) |
| `first_name` | string | None | Filter by first name (case-insensitive, partial match) |
| `last_name` | string | None | Filter by last name (case-insensitive, partial match) |
| `email` | string | None | Filter by email (case-insensitive, partial match) |
| `limit` | int | 20 | Max items to return (1-100) |
| `offset` | int | 0 | Number of items to skip |

### Query Parameters for Upcoming Birthdays

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Number of days to look ahead (1-365) |

### Search Semantics

- **Using `q`**: Searches first_name OR last_name OR email (OR semantics)
- **Using individual fields** (without `q`): Filters with AND semantics
- **All searches**: Case-insensitive partial matches (ILIKE)

## Contact Schema

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `first_name` | string | Yes | 1-255 characters |
| `last_name` | string | Yes | 1-255 characters |
| `email` | string | Yes | Valid email, unique, max 255 characters |
| `phone` | string | Yes | 7-20 characters, format: `^\+?[0-9()\-.\s]{7,20}$` |
| `birthday` | date | Yes | Format: YYYY-MM-DD |
| `notes` | string | No | Optional, max 5000 characters |

## Example Usage

### Create a Contact
```bash
curl -X POST "http://localhost:8000/api/contacts" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "birthday": "1990-05-15",
    "notes": "Met at conference"
  }'
```

### List Contacts with Search
```bash
# General search (OR semantics)
curl "http://localhost:8000/api/contacts?q=john"

# Filter by specific fields (AND semantics)
curl "http://localhost:8000/api/contacts?first_name=john&last_name=doe"

# Pagination
curl "http://localhost:8000/api/contacts?limit=10&offset=20"
```

### Get Upcoming Birthdays
```bash
# Next 7 days (default)
curl "http://localhost:8000/api/contacts/upcoming-birthdays"

# Next 30 days
curl "http://localhost:8000/api/contacts/upcoming-birthdays?days=30"
```

### Update a Contact
```bash
# Full update (PUT) - all fields required
curl -X PUT "http://localhost:8000/api/contacts/1" \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "email": "john.smith@example.com",
    "phone": "+1234567890",
    "birthday": "1990-05-15",
    "notes": "Updated"
  }'

# Partial update (PATCH) - only provided fields updated
curl -X PATCH "http://localhost:8000/api/contacts/1" \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated notes only"}'
```

### Delete a Contact
```bash
curl -X DELETE "http://localhost:8000/api/contacts/1"
```

## Birthday Calculation

The upcoming birthdays endpoint computes each contact's "next birthday":

1. If the birthday (month/day) has already passed this year → next year
2. If not yet passed → this year
3. Includes contacts whose next birthday falls within [today, today + days]

**Leap Year Handling:**
- Feb 29 birthdays are treated as Feb 28 on non-leap years

## Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=app

# Run specific test file
poetry run pytest tests/test_contacts.py -v
```

## Database Migrations

```bash
# Create a new migration (autogenerate from models)
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# View migration history
poetry run alembic history

# View current revision
poetry run alembic current
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── db.py             # Database engine and session management
│   ├── models.py         # SQLAlchemy 2.0 models
│   ├── schemas.py        # Pydantic v2 schemas
│   ├── crud.py           # Data access layer
│   ├── deps.py           # FastAPI dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py     # Settings management (pydantic-settings)
│   └── routers/
│       ├── __init__.py
│       └── contacts.py   # Contacts API router
├── alembic/
│   ├── env.py            # Alembic environment configuration
│   ├── script.py.mako    # Migration template
│   └── versions/         # Migration files (auto-generated)
├── tests/
│   ├── __init__.py
│   └── test_contacts.py  # API and unit tests
├── .env.example          # Environment template
├── .gitignore
├── alembic.ini           # Alembic configuration
├── docker-compose.yaml   # Docker Compose (db, api, migrate services)
├── Dockerfile            # Multi-stage Docker build with Poetry
├── pyproject.toml        # Poetry configuration and tool settings
├── poetry.lock           # Locked dependencies
├── requirements.txt      # Pip fallback for non-Poetry users
└── README.md
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:mysecretpassword@localhost:5432/contacts_db` | PostgreSQL connection string |
| `DB_ECHO` | `false` | Enable SQLAlchemy query logging |
| `APP_NAME` | `Contacts API` | Application name |
| `APP_VERSION` | `1.0.0` | Application version |
| `DEBUG` | `false` | Debug mode |
| `CORS_ORIGINS` | `["http://localhost:3000","http://localhost:8000"]` | Allowed CORS origins |

## Docker Services

| Service | Description |
|---------|-------------|
| `db` | PostgreSQL 15 database with health checks |
| `migrate` | Runs Alembic migrations on startup |
| `api` | FastAPI application (waits for db and migrate) |

## Troubleshooting

### Database Connection Issues

1. **Check PostgreSQL is running:**
   ```bash
   docker ps | grep postgres
   # or
   docker-compose ps
   ```

2. **Verify connection string in `.env`:**
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:mysecretpassword@localhost:5432/contacts_db
   ```

3. **Test connection:**
   ```bash
   psql -h localhost -U postgres -d contacts_db
   ```

### Migration Issues

1. **Reset migrations (development only):**
   ```bash
   poetry run alembic downgrade base
   poetry run alembic upgrade head
   ```

2. **Check current revision:**
   ```bash
   poetry run alembic current
   ```

3. **View migration history:**
   ```bash
   poetry run alembic history --verbose
   ```

### Docker Issues

1. **Rebuild containers:**
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

2. **View logs:**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f migrate
   ```

3. **Check container status:**
   ```bash
   docker-compose ps
   ```

## License

MIT
