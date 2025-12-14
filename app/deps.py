# app/deps.py
"""FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session

# Database session dependency
DBSession = Annotated[Session, Depends(get_session)]


# Pagination parameters
class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        limit: Annotated[
            int,
            Query(ge=1, le=100, description="Maximum number of items to return"),
        ] = 20,
        offset: Annotated[
            int,
            Query(ge=0, description="Number of items to skip"),
        ] = 0,
    ):
        self.limit = limit
        self.offset = offset


Pagination = Annotated[PaginationParams, Depends()]
