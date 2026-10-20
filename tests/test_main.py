from fastapi.testclient import TestClient
from datetime import datetime, timezone
from app.main import app

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.models import Base, ActivitySession

@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{test_db.as_posix()}")

    Base.metadata.create_all(test_engine)

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()

def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_stop_without_active_session(client):
    response = client.post("/sessions/stop")

    assert response.status_code == 409
    assert response.json() == {"detail": "No active session"}

def test_start_session(client):
    response = client.post(
        "/sessions/start", 
        json={"name": "Python", "activity_type": "work"}
    )
    data = response.json()

    assert response.status_code == 201
    assert data["name"] == "Python"
    assert data["activity_type"] == "work"
    assert data["started_at"] is not None
    assert data["ended_at"] is None
    assert data["id"] is not None
    assert isinstance(data["id"], int)

    get_response = client.get("/sessions")
    sessions = get_response.json()

    assert get_response.status_code == 200
    assert len(sessions) == 1
    assert sessions[0]["id"] == data["id"]

def test_switch_session(client):
    first= client.post("/sessions/start", json={"name": "Python", "activity_type": "work"})
    second= client.post("/sessions/start", json={"name": "Pydantic", "activity_type": "work"})

    assert first.status_code == 201
    assert second.status_code == 201

    get_response = client.get("/sessions")
    sessions = get_response.json()

    assert get_response.status_code == 200
    assert len(sessions) == 2

    first_session = next(
        activity for activity in sessions
        if activity["id"] == first.json()["id"]
    )

    second_session = next(
        activity for activity in sessions
        if activity["id"] == second.json()["id"]
    )

    assert first_session["ended_at"] is not None
    assert second_session["ended_at"] is None
    assert second_session["started_at"] == first_session["ended_at"]

def test_stop_session(client):
    first = client.post("/sessions/start", json={"name": "Python", "activity_type": "work"})
    response = client.post("/sessions/stop")

    assert first.status_code == 201
    assert response.status_code == 200
    assert first.json()["ended_at"] is None
    assert response.json()["ended_at"] is not None
    assert first.json()["id"] == response.json()["id"]

    get_response = client.get("/sessions")
    sessions = get_response.json()

    assert get_response.status_code == 200
    assert len(sessions) == 1
    assert sessions[0]["id"] == first.json()["id"]
    assert sessions[0]["ended_at"] == response.json()["ended_at"]

def test_start_invalid_name(client):
    response = client.post("/sessions/start", json={"name": " ", "activity_type": "work"})

    assert response.status_code == 422

    get_response = client.get("/sessions")
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
        first = ActivitySession(
            name="Python",
            activity_type="work",
            started_at=datetime.now(timezone.utc)
        )

        session.add(first)
        session.commit()

        # Second running activity
        second = ActivitySession(
            name="Exercise",
            activity_type="exercise",
            started_at=datetime.now(timezone.utc)
        )

        session.add(second)

        # Database should reject the second activity
        with pytest.raises(IntegrityError, match="uq_one_running_session"):
            session.commit()

        session.rollback()

    test_engine.dispose()