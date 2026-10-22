from datetime import datetime
from sqlalchemy.orm import Session

from app.activities.models import Activity
from tests.api_paths import ACTIVITIES_URL


def test_get_activities_by_day(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            Activity(
                name="Previous day",
                activity_type="work",
                started_at=datetime(2026, 10, 20, 12, 0),
                ended_at=datetime(2026, 10, 20, 13, 0)
            ),
            Activity(
                name="Requested day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 12, 0),
                ended_at=datetime(2026, 10, 21, 13, 0)
            ),
            Activity(
                name="Following day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 12, 0),
                ended_at=datetime(2026, 10, 22, 13, 0)
            ),
        ])
        session.commit()

    response = client.get(f"{ACTIVITIES_URL}?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = [activity["name"] for activity in data]

    assert names == ["Requested day"]


def test_day_lower_boundary(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            Activity(
                name="Previous day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 2, 0),
                ended_at=datetime(2026, 10, 21, 3, 0)
            ),
            Activity(
                name="Crossing boundary",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 2, 30),
                ended_at=datetime(2026, 10, 21, 3, 1)
            ),
            Activity(
                name="Current day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 3, 0),
                ended_at=datetime(2026, 10, 21, 4, 0)
            ),
        ])
        session.commit()

    response = client.get(f"{ACTIVITIES_URL}?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = {activity["name"] for activity in data}

    assert names == {"Crossing boundary", "Current day"}
    assert len(data) == 2

def test_day_upper_boundary(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            Activity(
                name="Current day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 2, 0),
                ended_at=datetime(2026, 10, 22, 3, 0)
            ),
            Activity(
                name="Crossing boundary",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 2, 30),
                ended_at=datetime(2026, 10, 22, 3, 1)
            ),
            Activity(
                name="Next day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 3, 0),
                ended_at=datetime(2026, 10, 22, 4, 0)
            ),
        ])
        session.commit()

    response = client.get(f"{ACTIVITIES_URL}?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = {activity["name"] for activity in data}

    assert names == {"Current day"}
    assert len(data) == 1
