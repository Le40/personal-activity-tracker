import pytest

from datetime import datetime
from sqlalchemy.orm import Session

from app.activities.models import Activity
from tests.api_paths import ACTIVITIES_URL

TEST_DAY = "2025-12-24"

@pytest.mark.parametrize("start, end, expected_status, expected_count", [
    # Existing Activity 10:00 - 12:00
    ("10:30", "11:00", 409, 1),  # New activity inside existing
    ("09:00", "13:00", 409, 1),  # New activity contains existing
    ("11:00", "13:00", 409, 1),  # Partial overlap
    ("10:00", "12:00", 409, 1),  # Identical intervals
    ("12:00", "13:00", 201, 2),  # Adjacent after
    ("09:00", "10:00", 201, 2),  # Adjacent before
])
def test_add_activity_overlaps(client, test_engine, 
    start: str, end: str, expected_status: int, expected_count: int):
    # Arrange
    with Session(test_engine) as db:
        db.add(Activity(
            name="Existing activity",
            activity_type="work",
            started_at = datetime.fromisoformat(f"{TEST_DAY}T10:00"),
            ended_at   = datetime.fromisoformat(f"{TEST_DAY}T12:00"),
        ))
        db.commit()

    # Act
    response = client.post(ACTIVITIES_URL, json={
        "name": "New activity",
        "activity_type": "work",
        "started_at": f"{TEST_DAY}T{start}:00Z",
        "ended_at": f"{TEST_DAY}T{end}:00Z"
    })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(
        f"{ACTIVITIES_URL}?start_date={TEST_DAY}&end_date={TEST_DAY}"
    )

    assert get_response.status_code == 200
    assert len(get_response.json()) == expected_count


@pytest.mark.parametrize("start, end, expected_status, expected_completed_count", [
    # Existing Activity 10:00 - None
    ("09:00", "10:00", 201, 1),  # New activity before running one
    ("09:00", "10:30", 409, 0),  # Partial overlap
    ("11:00", "13:00", 409, 0),  # Full overlap
])
def test_add_activity_overlaps_running_activity(client, test_engine, 
    start: str, end: str, expected_status: int, expected_completed_count: int):
    # Arrange
    with Session(test_engine) as db:
        db.add(Activity(
            name="Existing activity",
            activity_type="work",
            started_at = datetime.fromisoformat(f"{TEST_DAY}T10:00")
        ))
        db.commit()

    # Act
    response = client.post(ACTIVITIES_URL, json={
        "name": "New activity",
        "activity_type": "work",
        "started_at": f"{TEST_DAY}T{start}:00Z",
        "ended_at": f"{TEST_DAY}T{end}:00Z"
    })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(
        f"{ACTIVITIES_URL}?start_date={TEST_DAY}&end_date={TEST_DAY}"
    )
    assert get_response.status_code == 200
    assert len(get_response.json()) == expected_completed_count


@pytest.mark.parametrize("start, end, expected_status", [
    ("09:00", "12:00", 200),  # Touches both neighbors
    ("08:30", "12:30", 409),  # Overlaps both neighbors
    ("12:00", "13:00", 409),  # Identical to next activity
    ("12:30", "14:00", 409),  # Partially overlaps next
    ("13:00", "14:00", 200),  # Moves into a free slot
    ("10:00", "11:00", 200),  # Unchanged: must not overlap itself
])
def test_edit_activity_overlaps(client, test_engine, 
    start: str, end: str, expected_status: int):

    TESTED_START_TIME = "10:00"
    TESTED_END_TIME = "11:00"

    previous_activity = Activity(
        name="Previous activity",
        activity_type="work",
        started_at  =datetime.fromisoformat(f"{TEST_DAY}T08:00"),
        ended_at    =datetime.fromisoformat(f"{TEST_DAY}T09:00")
    )
    tested_activity = Activity(
        name="Tested activity",
        activity_type="work",
        started_at  =datetime.fromisoformat(f"{TEST_DAY}T{TESTED_START_TIME}"),
        ended_at    =datetime.fromisoformat(f"{TEST_DAY}T{TESTED_END_TIME}")
    )
    next_activity = Activity(
        name="next activity",
        activity_type="work",
        started_at  =datetime.fromisoformat(f"{TEST_DAY}T12:00"),
        ended_at    =datetime.fromisoformat(f"{TEST_DAY}T13:00")
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
            "started_at": f"{TEST_DAY}T{start}:00Z",
            "ended_at": f"{TEST_DAY}T{end}:00Z"
        })

    # Assert
    assert response.status_code == expected_status

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    data = get_response.json()
    if expected_status == 200:
        assert data["started_at"]   == f"{TEST_DAY}T{start}:00"
        assert data["ended_at"]     == f"{TEST_DAY}T{end}:00"
    else:
        assert data["started_at"]   == f"{TEST_DAY}T{TESTED_START_TIME}:00"
        assert data["ended_at"]     == f"{TEST_DAY}T{TESTED_END_TIME}:00"