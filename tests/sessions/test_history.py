import pytest

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models import Base, ActivitySession




def test_get_sessions_by_day(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            ActivitySession(
                name="Previous day",
                activity_type="work",
                started_at=datetime(2026, 10, 20, 12, 0),
                ended_at=datetime(2026, 10, 20, 13, 0)
            ),
            ActivitySession(
                name="Requested day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 12, 0),
                ended_at=datetime(2026, 10, 21, 13, 0)
            ),
            ActivitySession(
                name="Following day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 12, 0),
                ended_at=datetime(2026, 10, 22, 13, 0)
            ),
        ])
        session.commit()

    response = client.get("/sessions?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = [activity["name"] for activity in data]

    assert names == ["Requested day"]


def test_day_lower_boundary(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            ActivitySession(
                name="Previous day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 2, 0),
                ended_at=datetime(2026, 10, 21, 3, 0)
            ),
            ActivitySession(
                name="Crossing boundary",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 2, 30),
                ended_at=datetime(2026, 10, 21, 3, 1)
            ),
            ActivitySession(
                name="Current day",
                activity_type="work",
                started_at=datetime(2026, 10, 21, 3, 0),
                ended_at=datetime(2026, 10, 21, 4, 0)
            ),
        ])
        session.commit()

    response = client.get("/sessions?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = {activity["name"] for activity in data}

    assert names == {"Crossing boundary", "Current day"}
    assert len(data) == 2

def test_day_upper_boundary(client, test_engine):
    # PREPARE DATA
    with Session(test_engine) as session:
        session.add_all([
            ActivitySession(
                name="Current day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 2, 0),
                ended_at=datetime(2026, 10, 22, 3, 0)
            ),
            ActivitySession(
                name="Crossing boundary",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 2, 30),
                ended_at=datetime(2026, 10, 22, 3, 1)
            ),
            ActivitySession(
                name="Next day",
                activity_type="work",
                started_at=datetime(2026, 10, 22, 3, 0),
                ended_at=datetime(2026, 10, 22, 4, 0)
            ),
        ])
        session.commit()

    response = client.get("/sessions?day=2026-10-21")

    assert response.status_code == 200

    data = response.json()
    names = {activity["name"] for activity in data}

    assert names == {"Current day"}
    assert len(data) == 1
