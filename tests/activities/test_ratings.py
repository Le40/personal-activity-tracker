import pytest

from app.activities.options import ActivityType, EASE_RATING_ACTIVITY_TYPES
from tests.api_paths import ACTIVITIES_URL

# TEST EASE RATING AGAINST ACTIVITY TYPES
@pytest.mark.parametrize("activity_type", ActivityType)
def test_ease_rating_validation(client, activity_type):
    response = client.post(f"{ACTIVITIES_URL}/start", json={
        "name": "Test rating",
        "activity_type": activity_type.value,
        "ease_rating": 4
    })

    if activity_type in EASE_RATING_ACTIVITY_TYPES:
        assert response.status_code == 201
        assert response.json()["ease_rating"] == 4
    else:
        assert response.status_code == 422

# TEST EASE RATING AGAINST ACTIVITY TYPES
@pytest.mark.parametrize("activity_type", ActivityType)
def test_start_work_without_rating(client, activity_type):
    response = client.post(f"{ACTIVITIES_URL}/start", json={
        "name": "Test rating",
        "activity_type": activity_type.value,
    })

    assert response.status_code == 201
    assert response.json()["ease_rating"] is None

# TEST EASE RATING OUTSIDE BOUNDARY
@pytest.mark.parametrize("activity_type", EASE_RATING_ACTIVITY_TYPES)
@pytest.mark.parametrize("rating, expected_status", [
    (0, 422),
    (1, 201),
    (5, 201),
    (6, 422),
])
def test_rating_outside_boundary(client, activity_type, rating, expected_status):
    response = client.post(f"{ACTIVITIES_URL}/start", json={
        "name": "Test rating",
        "activity_type": activity_type.value,
        "ease_rating": rating
    })

    assert response.status_code == expected_status

# TEST CHANGE IN RATING
@pytest.mark.parametrize("activity_type", EASE_RATING_ACTIVITY_TYPES)
def test_ease_rating_change(client, activity_type):
    start_response = client.post(f"{ACTIVITIES_URL}/start", json={
        "name": "Test rating",
        "activity_type": activity_type.value,
        "ease_rating": 4
    })
    assert start_response.status_code == 201
    activity_id = start_response.json()["id"]

    update_response = client.put(f"{ACTIVITIES_URL}/{activity_id}", json={
        "name": "Test rating",
        "activity_type": activity_type.value,
        "ease_rating": 2
    })

    assert update_response.status_code == 200

    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    get_data = get_response.json()
    
    assert get_data["id"] == activity_id
    assert get_data["ease_rating"] == 2



# TEST CHANGE IN ACTIVITY TYPE WITH EASE RATING
@pytest.mark.parametrize("supported_type", EASE_RATING_ACTIVITY_TYPES)
@pytest.mark.parametrize("unsupported_type", set(ActivityType) - EASE_RATING_ACTIVITY_TYPES)
def test_change_to_unsupported_type_with_rating_is_rejected(
    client, supported_type, unsupported_type
):
    start_response = client.post(f"{ACTIVITIES_URL}/start", json={
        "name": "Test rating",
        "activity_type": supported_type.value,
        "ease_rating": 4
    })
    assert start_response.status_code == 201
    activity_id = start_response.json()["id"]

    update_response = client.put(f"{ACTIVITIES_URL}/{activity_id}", json={
        "name": "Test rating",
        "activity_type": unsupported_type.value,
        "ease_rating": 4
    })

    assert update_response.status_code == 422


    get_response = client.get(f"{ACTIVITIES_URL}/{activity_id}")
    assert get_response.status_code == 200

    get_data = get_response.json()
    
    assert get_data["id"] == activity_id
    assert get_data["activity_type"] == supported_type.value
    assert get_data["ease_rating"] == 4
