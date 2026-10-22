import pytest

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.activities.models import Base, Activity
from tests.api_paths import ACTIVITIES_URL


@pytest.mark.parametrize("started_at, ended_at, expected_status", [
    ("2026-10-21T08:00:00Z", "2026-10-21T09:00:00Z", 201),
    ("2026-10-21T08:00:00",  "2026-10-21T09:00:00Z", 422),
    ("2026-10-21T08:00:00Z", "2026-10-21T09:00:00",  422),
])
def test_adding_completed_activity_not_aware(client,
    started_at, ended_at, expected_status
):
    response = client.post(f"{ACTIVITIES_URL}", json={
        "name": "Python",
        "activity_type": "work", 
        "started_at": started_at,
        "ended_at": ended_at
        }
    )
    assert response.status_code == expected_status

@pytest.mark.parametrize("start, end, expected_status, expected_count", [
    ("10:30", "11:00", 409, 1),  # New activity inside existing
    ("09:00", "13:00", 409, 1),  # New activity contains existing
    ("11:00", "13:00", 409, 1),  # Partial overlap
    ("10:00", "12:00", 409, 1),  # Identical intervals
    ("12:00", "13:00", 201, 2),  # Adjacent after
    ("09:00", "10:00", 201, 2),  # Adjacent before
])
def test_activity_overlaps(client, test_engine, 
    start, end, expected_status, expected_count):
    # Arrange
    with Session(test_engine) as db:
        db.add(Activity(
            name="Existing activity",
            activity_type="work",
            started_at  =datetime(2026, 10, 21, 10, 0),
            ended_at    =datetime(2026, 10, 21, 12, 0)
        ))
        db.commit()

    # Act
    response = client.post(ACTIVITIES_URL, json={
        "name": "New activity",
        "activity_type": "work",
        "started_at": f"2026-10-21T{start}:00Z",
        "ended_at": f"2026-10-21T{end}:00Z"
    })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(ACTIVITIES_URL)
    assert get_response.status_code == 200
    assert len(get_response.json()) == expected_count


@pytest.mark.parametrize("start, end, expected_status, expected_count", [
    ("09:00", "10:00", 201, 2),  # New activity before running one
    ("09:00", "10:30", 409, 1),  # Partial overlap
    ("11:00", "13:00", 409, 1),  # Full overlap
])
def test_running_activity_overlaps(client, test_engine, 
    start, end, expected_status, expected_count):
    # Arrange
    with Session(test_engine) as db:
        db.add(Activity(
            name="Existing activity",
            activity_type="work",
            started_at=datetime(2026, 10, 21, 10, 0)
        ))
        db.commit()

    # Act
    response = client.post(ACTIVITIES_URL, json={
        "name": "New activity",
        "activity_type": "work",
        "started_at": f"2026-10-21T{start}:00Z",
        "ended_at": f"2026-10-21T{end}:00Z"
    })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(ACTIVITIES_URL)
    assert get_response.status_code == 200
    assert len(get_response.json()) == expected_count


@pytest.mark.parametrize("start, end, expected_status", [
    ("09:00", "12:00", 200),  # Touches both neighbors
    ("08:30", "12:30", 409),  # Overlaps both neighbors
    ("12:00", "13:00", 409),  # Identical to next activity
    ("12:30", "14:00", 409),  # Partially overlaps next
    ("13:00", "14:00", 200),  # Moves into a free slot
    ("10:00", "11:00", 200),  # Unchanged: must not overlap itself
])
def test_edit_activity_overlaps(client, test_engine, 
    start, end, expected_status):

    previous_activity = Activity(
        name="Previous activity",
        activity_type="work",
        started_at  =datetime(2026, 10, 21, 8, 0),
        ended_at    =datetime(2026, 10, 21, 9, 0)
    )
    tested_activity = Activity(
        name="Tested activity",
        activity_type="work",
        started_at  =datetime(2026, 10, 21, 10, 0),
        ended_at    =datetime(2026, 10, 21, 11, 0)
    )
    next_activity = Activity(
        name="next activity",
        activity_type="work",
        started_at  =datetime(2026, 10, 21, 12, 0),
        ended_at    =datetime(2026, 10, 21, 13, 0)
    )

    # Arrange
    with Session(test_engine) as db:
        db.add_all([previous_activity, tested_activity, next_activity])
        db.commit()
        activity_id = tested_activity.id

    # Act
    response = client.put(f"{ACTIVITIES_URL}/{activity_id}",
        json={
            "name": "Tested activity", 
            "activity_type": "work",
            "started_at": f"2026-10-21T{start}:00Z",
            "ended_at": f"2026-10-21T{end}:00Z"
        })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    data = get_response.json()
    if expected_status == 200:
        assert data["started_at"] == f"2026-10-21T{start}:00"
        assert data["ended_at"] == f"2026-10-21T{end}:00"
    else:
        assert data["started_at"] == "2026-10-21T10:00:00"
        assert data["ended_at"] == "2026-10-21T11:00:00"

def test_running_activity_times_cannot_be_updated(client):
    activity = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"name": "Python", "activity_type": "work"}
    )

    assert activity.status_code == 201
    data = activity.json()
    activity_id = data["id"]

    update_response = client.put(
        f"{ACTIVITIES_URL}/{activity_id}", 
        json={"name": "Python", "activity_type": "work",
              "started_at": "2026-10-21T11:00:00Z",
              "ended_at": "2026-10-21T12:00:00Z"}
    )
    assert update_response.status_code == 409

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200
    assert get_response.json() == data

@pytest.mark.parametrize("is_completed", [
    pytest.param(False, id="running"),
    pytest.param(True, id="completed")
])
def test_delete_activity(client, is_completed):
    activity = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"name": "Python", "activity_type": "work"}
    )
    assert activity.status_code == 201
    activity_id = activity.json()["id"]

    if is_completed:
        stop_response = client.post(f"{ACTIVITIES_URL}/stop")
        assert stop_response.status_code == 200

    delete_response = client.delete(f"{ACTIVITIES_URL}/{activity_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_activity(client):
    delete_response = client.delete(f"{ACTIVITIES_URL}/9999")
    assert delete_response.status_code == 404
