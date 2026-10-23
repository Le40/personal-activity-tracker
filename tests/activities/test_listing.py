import pytest
from sqlalchemy.orm import Session

from app.activities.models import Activity
from tests.api_paths import ACTIVITIES_URL
from tests.helpers import local_to_utc


@pytest.fixture
def activity_history(test_engine):

    # All test data is expressed in Bratislava local time.
    # The database stores it as naive UTC.

    records = [
        ("December 23 lower", "2025-12-22 23:30", "2025-12-23 05:01"),
        ("December 23 upper", "2025-12-24 04:00", "2025-12-24 05:00"),
        ("December 24 lower", "2025-12-23 23:30", "2025-12-24 05:01"),
        ("December 24 upper", "2025-12-25 04:00", "2025-12-25 05:00"),
        ("December 25 lower", "2025-12-24 23:30", "2025-12-25 05:01"),
        ("December 25 upper", "2025-12-26 04:00", "2025-12-26 05:00"),
        ("December 26 lower", "2025-12-25 23:30", "2025-12-26 05:01"),
        ("December 26 upper", "2025-12-27 04:00", "2025-12-27 05:00"),
    ]

    with Session(test_engine) as db:
        for name, start, end in records:
            db.add(Activity(
                name=name,
                activity_type="work",
                started_at=local_to_utc(start),
                ended_at=local_to_utc(end)
            ))

        db.commit()


@pytest.mark.parametrize(
    "start_date, end_date, expected_names",
    [
        pytest.param("2025-12-24", "2025-12-24",
            ["December 24 lower", "December 24 upper"],
            id="one-day"
        ),
        pytest.param("2025-12-24", "2025-12-25",
            ["December 24 lower", "December 24 upper",
             "December 25 lower", "December 25 upper"],
            id="multiple-days"
        )
    ]
)
def test_get_activities_by_dates(client, activity_history,
    start_date: str, end_date: str, expected_names: list[str]):

    response = client.get(
        f"{ACTIVITIES_URL}?start_date={start_date}&end_date={end_date}"
    )

    assert response.status_code == 200

    names = [activity["name"] for activity in response.json()]

    assert sorted(names) == sorted(expected_names)  


@pytest.mark.parametrize(
    "start_date, end_date, expected_status",
    [
        pytest.param("2025-12-01", "2025-12-31", 200, id="max-31-days"),
        pytest.param("2025-12-01", "2026-01-01", 422, id="exceeds-31-days"),
        pytest.param("2026-01-01", "2025-12-31", 422, id="reversed-dates"),
        pytest.param(None        , "2025-12-31", 422, id="missing-start-date"),
        pytest.param("2026-01-01", None,         422, id="missing-end-date"),
    ]
)
def test_date_range_validation(client,
    start_date: str | None, end_date: str | None, expected_status: int):

    params = {}

    if start_date is not None:
        params["start_date"] = start_date

    if end_date is not None:
        params["end_date"] = end_date

    response = client.get(ACTIVITIES_URL, params=params)

    assert response.status_code == expected_status

