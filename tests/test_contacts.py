# tests/test_contacts.py
"""Tests for the Contacts API."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.crud import _get_next_birthday, upcoming_birthdays
from app.db import get_session
from app.main import app
from app.models import Base, Contact

# Use SQLite for tests (in-memory)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_session():
    """Override database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Override the dependency
app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with fresh database."""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_contact_data():
    """Sample contact data for tests."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "birthday": "1990-05-15",
        "notes": "Test contact",
    }


@pytest.fixture
def sample_contact_data_2():
    """Second sample contact data for tests."""
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "+0987654321",
        "birthday": "1985-12-25",
        "notes": None,
    }


class TestContactCreate:
    """Tests for contact creation."""

    def test_create_contact_success(self, client, sample_contact_data):
        """Test successful contact creation."""
        response = client.post("/api/contacts", json=sample_contact_data)
        assert response.status_code == 201

        data = response.json()
        assert data["first_name"] == sample_contact_data["first_name"]
        assert data["last_name"] == sample_contact_data["last_name"]
        assert data["email"] == sample_contact_data["email"]
        assert data["phone"] == sample_contact_data["phone"]
        assert data["birthday"] == sample_contact_data["birthday"]
        assert data["notes"] == sample_contact_data["notes"]
        assert "id" in data

    def test_create_contact_duplicate_email(self, client, sample_contact_data):
        """Test that duplicate email returns 409."""
        # Create first contact
        client.post("/api/contacts", json=sample_contact_data)

        # Try to create with same email
        response = client.post("/api/contacts", json=sample_contact_data)
        assert response.status_code == 409

    def test_create_contact_invalid_email(self, client, sample_contact_data):
        """Test that invalid email returns 422."""
        sample_contact_data["email"] = "invalid-email"
        response = client.post("/api/contacts", json=sample_contact_data)
        assert response.status_code == 422

    def test_create_contact_invalid_phone(self, client, sample_contact_data):
        """Test that invalid phone returns 422."""
        sample_contact_data["phone"] = "abc"
        response = client.post("/api/contacts", json=sample_contact_data)
        assert response.status_code == 422


class TestContactRead:
    """Tests for contact retrieval."""

    def test_get_contact_by_id(self, client, sample_contact_data):
        """Test getting a contact by ID."""
        # Create contact
        create_response = client.post("/api/contacts", json=sample_contact_data)
        contact_id = create_response.json()["id"]

        # Get contact
        response = client.get(f"/api/contacts/{contact_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == contact_id
        assert data["email"] == sample_contact_data["email"]

    def test_get_contact_not_found(self, client):
        """Test getting non-existent contact returns 404."""
        response = client.get("/api/contacts/99999")
        assert response.status_code == 404


class TestContactList:
    """Tests for contact listing and search."""

    def test_list_contacts_empty(self, client):
        """Test listing contacts when none exist."""
        response = client.get("/api/contacts")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_contacts_with_data(
        self, client, sample_contact_data, sample_contact_data_2
    ):
        """Test listing contacts with data."""
        client.post("/api/contacts", json=sample_contact_data)
        client.post("/api/contacts", json=sample_contact_data_2)

        response = client.get("/api/contacts")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    def test_list_contacts_search_q(
        self, client, sample_contact_data, sample_contact_data_2
    ):
        """Test general search with q parameter."""
        client.post("/api/contacts", json=sample_contact_data)
        client.post("/api/contacts", json=sample_contact_data_2)

        # Search for "john" - should find John Doe
        response = client.get("/api/contacts?q=john")
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["first_name"] == "John"

    def test_list_contacts_search_by_email(
        self, client, sample_contact_data, sample_contact_data_2
    ):
        """Test search by email."""
        client.post("/api/contacts", json=sample_contact_data)
        client.post("/api/contacts", json=sample_contact_data_2)

        response = client.get("/api/contacts?email=jane")
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["email"] == "jane.smith@example.com"

    def test_list_contacts_case_insensitive(self, client, sample_contact_data):
        """Test that search is case-insensitive."""
        client.post("/api/contacts", json=sample_contact_data)

        # Search with different case
        response = client.get("/api/contacts?q=JOHN")
        data = response.json()
        assert len(data["items"]) == 1

    def test_list_contacts_pagination(self, client, sample_contact_data):
        """Test pagination."""
        # Create multiple contacts
        for i in range(5):
            data = sample_contact_data.copy()
            data["email"] = f"contact{i}@example.com"
            client.post("/api/contacts", json=data)

        # Test limit
        response = client.get("/api/contacts?limit=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

        # Test offset
        response = client.get("/api/contacts?limit=2&offset=2")
        data = response.json()
        assert len(data["items"]) == 2
        assert data["offset"] == 2


class TestContactUpdate:
    """Tests for contact updates."""

    def test_update_contact_full(self, client, sample_contact_data):
        """Test full contact update (PUT)."""
        # Create contact
        create_response = client.post("/api/contacts", json=sample_contact_data)
        contact_id = create_response.json()["id"]

        # Update contact
        updated_data = sample_contact_data.copy()
        updated_data["first_name"] = "Johnny"
        updated_data["notes"] = "Updated notes"

        response = client.put(f"/api/contacts/{contact_id}", json=updated_data)
        assert response.status_code == 200

        data = response.json()
        assert data["first_name"] == "Johnny"
        assert data["notes"] == "Updated notes"

    def test_update_contact_partial(self, client, sample_contact_data):
        """Test partial contact update (PATCH)."""
        # Create contact
        create_response = client.post("/api/contacts", json=sample_contact_data)
        contact_id = create_response.json()["id"]

        # Partial update
        response = client.patch(
            f"/api/contacts/{contact_id}",
            json={"notes": "New notes only"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["notes"] == "New notes only"
        assert data["first_name"] == sample_contact_data["first_name"]

    def test_update_contact_not_found(self, client, sample_contact_data):
        """Test updating non-existent contact returns 404."""
        response = client.put("/api/contacts/99999", json=sample_contact_data)
        assert response.status_code == 404

    def test_update_contact_duplicate_email(
        self, client, sample_contact_data, sample_contact_data_2
    ):
        """Test updating with existing email returns 409."""
        # Create two contacts
        client.post("/api/contacts", json=sample_contact_data)
        create_response = client.post("/api/contacts", json=sample_contact_data_2)
        contact_id = create_response.json()["id"]

        # Try to update second contact with first contact's email
        response = client.patch(
            f"/api/contacts/{contact_id}",
            json={"email": sample_contact_data["email"]},
        )
        assert response.status_code == 409


class TestContactDelete:
    """Tests for contact deletion."""

    def test_delete_contact(self, client, sample_contact_data):
        """Test deleting a contact."""
        # Create contact
        create_response = client.post("/api/contacts", json=sample_contact_data)
        contact_id = create_response.json()["id"]

        # Delete contact
        response = client.delete(f"/api/contacts/{contact_id}")
        assert response.status_code == 200

        # Verify deletion
        get_response = client.get(f"/api/contacts/{contact_id}")
        assert get_response.status_code == 404

    def test_delete_contact_not_found(self, client):
        """Test deleting non-existent contact returns 404."""
        response = client.delete("/api/contacts/99999")
        assert response.status_code == 404


class TestUpcomingBirthdays:
    """Tests for upcoming birthdays endpoint."""

    def test_upcoming_birthdays_empty(self, client):
        """Test upcoming birthdays with no contacts."""
        response = client.get("/api/contacts/upcoming-birthdays")
        assert response.status_code == 200
        assert response.json() == []

    def test_upcoming_birthdays_with_contacts(self, client):
        """Test upcoming birthdays with contacts."""
        today = date.today()

        # Create contact with birthday in 3 days
        birthday_soon = today + timedelta(days=3)
        contact_data = {
            "first_name": "Birthday",
            "last_name": "Soon",
            "email": "soon@example.com",
            "phone": "+1234567890",
            "birthday": birthday_soon.replace(year=1990).isoformat(),
        }
        client.post("/api/contacts", json=contact_data)

        # Create contact with birthday far away
        birthday_far = today + timedelta(days=100)
        contact_data_far = {
            "first_name": "Birthday",
            "last_name": "Far",
            "email": "far@example.com",
            "phone": "+1234567890",
            "birthday": birthday_far.replace(year=1990).isoformat(),
        }
        client.post("/api/contacts", json=contact_data_far)

        response = client.get("/api/contacts/upcoming-birthdays?days=7")
        data = response.json()

        assert len(data) == 1
        assert data[0]["email"] == "soon@example.com"

    def test_upcoming_birthdays_custom_days(self, client):
        """Test upcoming birthdays with custom days parameter."""
        today = date.today()

        # Create contact with birthday in 20 days
        birthday = today + timedelta(days=20)
        contact_data = {
            "first_name": "Birthday",
            "last_name": "Twenty",
            "email": "twenty@example.com",
            "phone": "+1234567890",
            "birthday": birthday.replace(year=1990).isoformat(),
        }
        client.post("/api/contacts", json=contact_data)

        # Should not appear in 7-day window
        response = client.get("/api/contacts/upcoming-birthdays?days=7")
        assert len(response.json()) == 0

        # Should appear in 30-day window
        response = client.get("/api/contacts/upcoming-birthdays?days=30")
        assert len(response.json()) == 1


class TestBirthdayCalculation:
    """Unit tests for birthday calculation logic."""

    def test_get_next_birthday_this_year(self):
        """Test birthday that hasn't occurred yet this year."""
        today = date(2024, 6, 15)
        birthday = date(1990, 12, 25)

        next_bday = _get_next_birthday(birthday, today)
        assert next_bday == date(2024, 12, 25)

    def test_get_next_birthday_next_year(self):
        """Test birthday that already passed this year."""
        today = date(2024, 6, 15)
        birthday = date(1990, 3, 10)

        next_bday = _get_next_birthday(birthday, today)
        assert next_bday == date(2025, 3, 10)

    def test_get_next_birthday_today(self):
        """Test birthday that is today."""
        today = date(2024, 6, 15)
        birthday = date(1990, 6, 15)

        next_bday = _get_next_birthday(birthday, today)
        assert next_bday == date(2024, 6, 15)

    def test_get_next_birthday_leap_year(self):
        """Test Feb 29 birthday on non-leap year."""
        today = date(2023, 1, 1)  # 2023 is not a leap year
        birthday = date(2000, 2, 29)

        next_bday = _get_next_birthday(birthday, today)
        # Should use Feb 28 since 2023 is not a leap year
        assert next_bday == date(2023, 2, 28)

    def test_get_next_birthday_leap_year_actual(self):
        """Test Feb 29 birthday on leap year."""
        today = date(2024, 1, 1)  # 2024 is a leap year
        birthday = date(2000, 2, 29)

        next_bday = _get_next_birthday(birthday, today)
        assert next_bday == date(2024, 2, 29)

    def test_upcoming_birthdays_with_fixed_date(self, db_session: Session):
        """Test upcoming birthdays CRUD function with fixed date."""
        # Create contacts directly in DB
        today = date(2024, 6, 15)

        # Birthday in 3 days
        contact1 = Contact(
            first_name="Soon",
            last_name="Birthday",
            email="soon@test.com",
            phone="+1111111111",
            birthday=date(1990, 6, 18),  # 3 days from today
        )

        # Birthday in 10 days
        contact2 = Contact(
            first_name="Later",
            last_name="Birthday",
            email="later@test.com",
            phone="+2222222222",
            birthday=date(1985, 6, 25),  # 10 days from today
        )

        # Birthday already passed
        contact3 = Contact(
            first_name="Passed",
            last_name="Birthday",
            email="passed@test.com",
            phone="+3333333333",
            birthday=date(1995, 1, 1),  # Already passed
        )

        db_session.add_all([contact1, contact2, contact3])
        db_session.commit()

        # Get upcoming birthdays within 7 days
        result = upcoming_birthdays(db_session, days=7, today=today)

        assert len(result) == 1
        assert result[0].email == "soon@test.com"

        # Get upcoming birthdays within 15 days
        result = upcoming_birthdays(db_session, days=15, today=today)

        assert len(result) == 2
        emails = [c.email for c in result]
        assert "soon@test.com" in emails
        assert "later@test.com" in emails


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
