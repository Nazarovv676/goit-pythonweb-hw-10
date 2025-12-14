# app/crud.py
"""CRUD operations for contacts - pure data access layer."""

from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Contact
from app.schemas import ContactCreate, ContactUpdate


def create_contact(session: Session, data: ContactCreate) -> Contact:
    """Create a new contact."""
    contact = Contact(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        birthday=data.birthday,
        notes=data.notes,
    )
    session.add(contact)
    session.flush()
    return contact


def get_contact(session: Session, contact_id: int) -> Contact | None:
    """Get a contact by ID."""
    stmt = select(Contact).where(Contact.id == contact_id)
    return session.execute(stmt).scalar_one_or_none()


def get_contact_by_email(session: Session, email: str) -> Contact | None:
    """Get a contact by email."""
    stmt = select(Contact).where(func.lower(Contact.email) == func.lower(email))
    return session.execute(stmt).scalar_one_or_none()


def list_contacts(
    session: Session,
    *,
    q: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Contact], int]:
    """
    List contacts with optional filters and pagination.

    Search behavior:
    - If 'q' is provided: searches first_name OR last_name OR email (OR semantics)
    - If individual fields are provided without 'q': uses AND semantics
    - All searches are case-insensitive using ILIKE

    Returns:
        Tuple of (contacts list, total count)
    """
    stmt = select(Contact)
    count_stmt = select(func.count(Contact.id))

    # Build filter conditions
    if q:
        # General search: OR semantics across first_name, last_name, email
        search_pattern = f"%{q}%"
        or_conditions = or_(
            Contact.first_name.ilike(search_pattern),
            Contact.last_name.ilike(search_pattern),
            Contact.email.ilike(search_pattern),
        )
        stmt = stmt.where(or_conditions)
        count_stmt = count_stmt.where(or_conditions)
    else:
        # Individual field filters: AND semantics
        conditions = []
        if first_name:
            conditions.append(Contact.first_name.ilike(f"%{first_name}%"))
        if last_name:
            conditions.append(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            conditions.append(Contact.email.ilike(f"%{email}%"))

        if conditions:
            for condition in conditions:
                stmt = stmt.where(condition)
                count_stmt = count_stmt.where(condition)

    # Get total count
    total = session.execute(count_stmt).scalar() or 0

    # Apply pagination and ordering
    stmt = stmt.order_by(Contact.id).offset(offset).limit(limit)
    contacts = list(session.execute(stmt).scalars().all())

    return contacts, total


def update_contact(session: Session, contact: Contact, data: ContactUpdate) -> Contact:
    """Update an existing contact with provided fields."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    session.flush()
    return contact


def delete_contact(session: Session, contact: Contact) -> None:
    """Delete a contact."""
    session.delete(contact)
    session.flush()


def upcoming_birthdays(
    session: Session,
    days: int = 7,
    today: date | None = None,
) -> list[Contact]:
    """
    Get contacts with birthdays in the next N days.

    This function computes each contact's "next birthday" considering year rollover:
    - If the birthday (month/day) has already passed this year, the next birthday
      is next year
    - Otherwise, it's this year

    For leap year birthdays (Feb 29):
    - On non-leap years, Feb 29 birthdays are treated as Feb 28

    Args:
        session: Database session
        days: Number of days to look ahead (default: 7, range: 1-365)
        today: Reference date (default: current date in UTC)

    Returns:
        List of contacts with upcoming birthdays, ordered by their next birthday date
    """
    if today is None:
        today = date.today()

    end_date = today + timedelta(days=days)

    # Fetch all contacts and filter in Python for accurate year rollover handling
    # This approach is more maintainable and handles edge cases correctly
    # For large datasets, consider database-specific SQL optimization
    stmt = select(Contact)
    all_contacts = list(session.execute(stmt).scalars().all())

    result = []
    for contact in all_contacts:
        next_bday = _get_next_birthday(contact.birthday, today)
        if today <= next_bday <= end_date:
            result.append((next_bday, contact))

    # Sort by next birthday date
    result.sort(key=lambda x: x[0])
    return [contact for _, contact in result]


def _get_next_birthday(birthday: date, reference_date: date) -> date:
    """
    Calculate the next occurrence of a birthday relative to reference_date.

    Handles leap year edge case: Feb 29 birthdays become Feb 28 on non-leap years.
    """
    this_year = reference_date.year

    # Try to create birthday this year
    try:
        bday_this_year = birthday.replace(year=this_year)
    except ValueError:
        # Feb 29 on non-leap year -> use Feb 28
        bday_this_year = date(this_year, 2, 28)

    if bday_this_year >= reference_date:
        return bday_this_year

    # Birthday already passed this year, use next year
    next_year = this_year + 1
    try:
        return birthday.replace(year=next_year)
    except ValueError:
        # Feb 29 on non-leap year -> use Feb 28
        return date(next_year, 2, 28)
