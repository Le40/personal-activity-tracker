import pytest

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Base, Activity
from tests.api_paths import ACTIVITIES_URL


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_nonexistent_activity(client):
    response = client.get(f"{ACTIVITIES_URL}/999")

    assert response.status_code == 404

def test_stop_without_active_activity(client):
    response = client.post(f"{ACTIVITIES_URL}/stop")

    assert response.status_code == 409
    assert response.json() == {"detail": "No active activity"}

def test_start_session(client):
    response = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"name": "Python", "activity_type": "work"}
    )
    data = response.json()
    activity_id = data["id"]

    assert response.status_code == 201
    assert data["name"] == "Python"
    assert data["activity_type"] == "work"
    assert data["started_at"] is not None
    assert data["ended_at"] is None
    assert data["id"] is not None
    assert isinstance(data["id"], int)

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    get_data = get_response.json()
    assert get_response.json() == data

def test_switch_activity(client):
    first= client.post(f"{ACTIVITIES_URL}/start", json={"name": "Python", "activity_type": "work"})
    second= client.post(f"{ACTIVITIES_URL}/start", json={"name": "Pydantic", "activity_type": "work"})

    assert first.status_code == 201
    assert second.status_code == 201

    get_response = client.get(f"{ACTIVITIES_URL}")
    activities = get_response.json()

    assert get_response.status_code == 200
    assert len(activities) == 2

    first_activity = next(
        activity for activity in activities
        if activity["id"] == first.json()["id"]
    )

    second_activity = next(
        activity for activity in activities
        if activity["id"] == second.json()["id"]
    )

    assert first_activity["ended_at"] is not None
    assert second_activity["ended_at"] is None
    assert second_activity["started_at"] == first_activity["ended_at"]

def test_stop_activity(client):
    start_response = client.post(f"{ACTIVITIES_URL}/start", json={"name": "Python", "activity_type": "work"})
    assert start_response.status_code == 201

    start_data = start_response.json()
    activity_id = start_data["id"]
    assert start_data["ended_at"] is None

    stop_response = client.post(f"{ACTIVITIES_URL}/stop")
    assert stop_response.status_code == 200

    stop_data = stop_response.json()
    assert stop_data["ended_at"] is not None
    assert stop_data["id"] == start_data["id"]

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    get_data = get_response.json()

    assert get_data["id"] == start_data["id"]
    assert get_data["ended_at"] == stop_data["ended_at"]

def test_start_invalid_name(client):
    response = client.post(f"{ACTIVITIES_URL}/start", json={"name": " ", "activity_type": "work"})

    assert response.status_code == 422

    get_response = client.get(f"{ACTIVITIES_URL}")
    sessions = get_response.json()

    assert get_response.status_code == 200
    assert len(sessions) == 0

def test_only_one_running_session_allowed(tmp_path):
    # Create an isolated test database
    test_db = tmp_path / "constraint.db"
    test_engine = create_engine(f"sqlite:///{test_db.as_posix()}")

    # Create tables and indexes
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # First running activity
        first = Activity(
            name="Python",
            activity_type="work",
            started_at=datetime.now(timezone.utc)
        )

        session.add(first)
        session.commit()

        # Second running activity
        second = Activity(
            name="Exercise",
            activity_type="exercise",
            started_at=datetime.now(timezone.utc)
        )

        session.add(second)

        # Database should reject the second activity
        with pytest.raises(IntegrityError, match="uq_one_running_activity"):
            session.commit()

        session.rollback()

    test_engine.dispose()

    def test_update_session(client):
        response = client.post(
            f"{ACTIVITIES_URL}/start", json={"name": "python", "activity_type": "work"})
        assert response.status_code == 201

        original = response.json()

        update_response = client.put(
            f"{ACTIVITIES_URL}/{response.json()["id"]}", 
            json={"name": "python88", "activity_type": "work", "notes": "some notes"})

        assert update_response.status_code == 200

        updated = update_response.json()

        assert updated["id"] == original["id"]
        assert updated["started_at"] == original["started_at"]
        assert updated["ended_at"] is None

        assert updated["name"] == "python88"
        assert updated["activity_type"] == "meal"
        assert updated["notes"] == "some notes"