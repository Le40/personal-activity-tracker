from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.activities.models import Activity, Base
from tests.api_paths import ACTIVITIES_URL


@pytest.mark.parametrize("create_activity , expected_status",
    [
        (True, 200), 
        (False, 204)
    ])
def test_get_running_activity(client, create_activity: bool, expected_status: int):
    if create_activity:
        start_response = client.post(f"{ACTIVITIES_URL}/start",
            json={"activity_type": "work"})
        assert start_response.status_code == 201
    
    response = client.get(f"{ACTIVITIES_URL}/current")

    assert response.status_code == expected_status

    if create_activity:
        assert response.json() == start_response.json()
    else:
        assert response.content == b""


def test_stop_without_active_activity(client):
    response = client.post(f"{ACTIVITIES_URL}/stop")

    assert response.status_code == 409
    assert response.json() == {"detail": "No active activity"}


def test_start_activity(client):
    response = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"activity_type": "work"}
    )
    data = response.json()
    activity_id = data["id"]

    assert response.status_code == 201
    assert data["activity_type"] == "work"
    assert data["started_at"] is not None
    assert data["ended_at"] is None
    assert data["id"] is not None
    assert isinstance(data["id"], int)

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    assert get_response.json() == data


def test_start_invalid_activity(client):
    response = client.post(f"{ACTIVITIES_URL}/start", json={"name": " ", "activity_type": "xxxx"})

    assert response.status_code == 422

    get_response = client.get(f"{ACTIVITIES_URL}/current")

    assert get_response.status_code == 204


@pytest.mark.parametrize("value", ["", "   ", None])
def test_start_empty_optional_fields(client, value: str | None):
    response = client.post(
        f"{ACTIVITIES_URL}/start",
        json={
            "activity_type": "work",
            "name": value,
            "notes": value,
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] is None
    assert data["notes"] is None


def test_switch_activity(client):
    first = client.post(
        f"{ACTIVITIES_URL}/start",
        json={"activity_type": "work"}
    )

    second = client.post(
        f"{ACTIVITIES_URL}/start",
        json={"name": "Pydantic", "activity_type": "work"}
    )

    assert first.status_code == 201
    assert second.status_code == 201

    first_id = first.json()["id"]
    second_id = second.json()["id"]

    first_response = client.get(f"{ACTIVITIES_URL}/{first_id}")
    second_response = client.get(f"{ACTIVITIES_URL}/{second_id}")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_activity = first_response.json()
    second_activity = second_response.json()

    assert first_activity["ended_at"] is not None
    assert second_activity["ended_at"] is None
    assert second_activity["started_at"] == first_activity["ended_at"]


def test_stop_activity(client):
    start_response = client.post(f"{ACTIVITIES_URL}/start", json={"activity_type": "work"})
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


def test_only_one_running_activity_allowed(tmp_path):
    # Create an isolated test database
    test_db = tmp_path / "constraint.db"
    test_engine = create_engine(f"sqlite:///{test_db.as_posix()}")

    # Create tables and indexes
    Base.metadata.create_all(test_engine)

    with Session(test_engine) as db:
        # First running activity
        first = Activity(
            name="Python",
            activity_type="work",
            started_at=datetime.now(UTC)
        )

        db.add(first)
        db.commit()

        # Second running activity
        second = Activity(
            name="Exercise",
            activity_type="exercise",
            started_at=datetime.now(UTC)
        )

        db.add(second)

        # Database should reject the second activity
        with pytest.raises(IntegrityError, match="uq_one_running_activity"):
            db.commit()

        db.rollback()

    test_engine.dispose()


def test_update_running_activity(client):
    response = client.post(
        f"{ACTIVITIES_URL}/start", json={"name": "python", "activity_type": "work"})
    assert response.status_code == 201

    original = response.json()

    update_response = client.put(
        f"{ACTIVITIES_URL}/{response.json()["id"]}", 
        json={"name": "python88", "activity_type": "meal", "notes": "some notes"})

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["id"] == original["id"]
    assert updated["started_at"] == original["started_at"]
    assert updated["ended_at"] is None

    assert updated["name"] == "python88"
    assert updated["activity_type"] == "meal"
    assert updated["notes"] == "some notes"