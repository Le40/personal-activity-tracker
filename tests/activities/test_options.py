
from app.activities.options import ActivityType, EASE_RATING_ACTIVITY_TYPES, EASE_LABELS
from tests.api_paths import ACTIVITIES_URL

def test_options(client):
    response = client.get(f"{ACTIVITIES_URL}/options")
    assert response.status_code == 200

    data = response.json()
    options = data["activity_types"]
    ratings = data["ease_ratings"]

    # ARE ACTIVITY TYPES COMPLETELY RETURNED
    assert {item["value"] for item in options} == {
        activity.value for activity in ActivityType
    }

    # ARE ONLY THE RIGHT ONES HAVE EASE OF WORK RATING
    for item in options:
        activity = ActivityType(item["value"])

        assert item["supports_ease_rating"] == (
            activity in EASE_RATING_ACTIVITY_TYPES
        )
    # ARE EASE OF WORK TYPES COMPLETELY RETURNED
    actual_ratings = {item["value"]: item["label"] for item in ratings}
    expected_ratings = {rating.value: label for rating, label in EASE_LABELS.items()}
    assert actual_ratings == expected_ratings