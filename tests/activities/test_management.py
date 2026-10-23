import pytest

from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.activities.models import Activity
from tests.api_paths import ACTIVITIES_URL
from tests.conftest import test_engine

TEST_DAY = "2026-10-21"


@pytest.mark.parametrize("started_at, ended_at, expected_status", [
    ("2026-10-21T08:00:00Z", "2026-10-21T09:00:00Z", 201),
    ("2026-10-21T08:00:00",  "2026-10-21T09:00:00Z", 422),
    ("2026-10-21T08:00:00Z", "2026-10-21T09:00:00",  422),
])
def test_adding_activity_dates_not_tz_aware(client,
    started_at: str, ended_at: str, expected_status: int
):
    response = client.post(f"{ACTIVITIES_URL}", json={
        "activity_type": "work", 
        "started_at": started_at,
        "ended_at": ended_at
        }
    )
    assert response.status_code == expected_status


# CHANGE
def test_running_activity_times_cannot_be_updated(client):
    activity = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"activity_type": "work"}
    )

    assert activity.status_code == 201
    data = activity.json()
    activity_id = data["id"]

    update_response = client.put(
        f"{ACTIVITIES_URL}/{activity_id}", 
        json={"activity_type": "work",
              "started_at"  : f"{TEST_DAY}T11:00:00Z",
              "ended_at"    : f"{TEST_DAY}T12:00:00Z"}
    )
    assert update_response.status_code == 409

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200
    assert get_response.json() == data


@pytest.mark.parametrize("is_completed", [
    pytest.param(False, id="running"),
    pytest.param(True, id="completed")
])
def test_delete_activity(client, is_completed: bool):
    activity = client.post(
        f"{ACTIVITIES_URL}/start", 
        json={"activity_type": "work"}
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


def test_get_nonexistent_activity(client):
    response = client.get(f"{ACTIVITIES_URL}/999")

    assert response.status_code == 404


def test_clear_activity_name_and_notes(client):
    # Arrange
    start_response = client.post(f"{ACTIVITIES_URL}/start",
        json={
            "activity_type": "work",
            "notes": "Learning FastAPI"
        }
    )
    assert start_response.status_code == 201

    activity_id = start_response.json()["id"]

    # Act
    response = client.put(f"{ACTIVITIES_URL}/{activity_id}",
        json={
            "name": "",
            "activity_type": "work",
            "notes": "   "
        }
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["name"] is None
    assert response.json()["notes"] is None


FUTURE_DATE_CASES = [
    pytest.param(timedelta(hours=1), timedelta(hours=2), "started_at", id="future-start",),
    pytest.param(timedelta(days=-1), timedelta(hours=1), "ended_at", id="future-end",),
]
@pytest.mark.parametrize("method",["POST", "PUT"])
@pytest.mark.parametrize("start_offset, end_offset, invalid_field",FUTURE_DATE_CASES)
def test_create_and_update_reject_future_dates(client, test_engine,
    method: str, start_offset: timedelta, end_offset: timedelta, invalid_field: str,
):
    now = datetime.now(timezone.utc)

    started_at = (now + start_offset).isoformat()
    ended_at = (now + end_offset).isoformat()
    payload = {
        "activity_type": "work",
        "started_at": started_at,
        "ended_at": ended_at
    }
    url = ACTIVITIES_URL

    if method == "PUT":
        activity =Activity(
            activity_type="work",
            started_at  =datetime.fromisoformat(f"{TEST_DAY}T08:00"),
            ended_at    =datetime.fromisoformat(f"{TEST_DAY}T09:00")
        )
        with Session(test_engine) as db:
            db.add(activity)
            db.commit()
            activity_id = activity.id
        
        url += f"/{activity_id}"

    response = client.request(method, url, json=payload)    

    assert response.status_code == 422
    errors = response.json()["detail"]

    assert any(error["loc"][-1] == invalid_field for error in errors)