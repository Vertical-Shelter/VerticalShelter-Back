import pytest
from concurrent.futures import ThreadPoolExecutor

from .conftest import CLIMBINGLOCATION_ID, HEADERS


def test_list_by_name_without_name(client):
    response = client.get("/api/v1/climbingLocation/list-by-name/?name=")
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

def test_get_climbingLocation_unauthorized(client):
    response = client.get(
        f"/api/v1/climbingLocation/?climbingLocation_id={CLIMBINGLOCATION_ID}",
        headers={} # no headers
    )
    assert response.status_code == 401

def test_get_climbingLocation(client):
    response = client.get(
        f"/api/v1/climbingLocation/?climbingLocation_id={CLIMBINGLOCATION_ID}",
        headers=HEADERS
    )
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)
    assert "id" in response_json
    assert response_json["id"] == CLIMBINGLOCATION_ID

def test_get_climbingLocation_not_found(client):
    response = client.get(
        f"/api/v1/climbingLocation/?climbingLocation_id=willnotbefound",
        headers=HEADERS
    )
    assert response.status_code == 400
    assert response.json() == {"detail": {"error": "ClimbingLocation not found"}}


@pytest.mark.skip # this test is expensive
def test_get_climbingLocation_300(client, num_users=300, num_workers=100):

    def get_climbing_location(i):
        response = client.get(
            f"/api/v1/climbingLocation/?climbingLocation_id={CLIMBINGLOCATION_ID}",
            headers=HEADERS
        )
        return response
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        responses = executor.map(get_climbing_location, range(num_users))

        for response in responses:
            assert response.status_code == 200
            response_json = response.json()
            assert isinstance(response_json, dict)
            assert "id" in response_json
            assert response_json["id"] == CLIMBINGLOCATION_ID