# app/main.py
"""FastAPI application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import get_settings
from app.routers import contacts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Debug mode: %s", settings.debug)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="""
## Contacts API

A REST API for managing contacts with the following features:

- **CRUD Operations**: Create, read, update, and delete contacts
- **Search**: Search contacts by name or email with flexible filtering
- **Upcoming Birthdays**: Find contacts with birthdays in the next N days

### Search Behavior

- Use `q` parameter for general search (OR semantics across first_name, last_name, email)
- Use individual field parameters for precise filtering (AND semantics)
- All searches are case-insensitive partial matches

### Birthday Calculation

The upcoming birthdays endpoint calculates each contact's next birthday:
- If birthday has passed this year → shows next year's date
- Handles leap year birthdays (Feb 29 → Feb 28 on non-leap years)
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,  # Disable default, use custom
    openapi_url="/openapi.json",
)


@app.get("/redoc", include_in_schema=False)
def redoc_html() -> HTMLResponse:
    """Custom ReDoc page with stable version."""
    return get_redoc_html(
        openapi_url=app.openapi_url or "/openapi.json",
        title=f"{app.title} - ReDoc",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@2.1.3/bundles/redoc.standalone.js",
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(contacts.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect root to API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}
