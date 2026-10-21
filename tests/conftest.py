import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_session
from app.models import Base


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