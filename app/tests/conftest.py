# tests/conftest.py
import pytest
import datetime
import json

from fastapi.testclient import TestClient

from ..settings import app
from .. import main


CLIMBINGLOCATION_ID = "q0gQ5mcCt4kVPSwPZhqQ"
HEADERS = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4NDYzMjA1NDMsInN1YiI6IjNLQTUxSEF2VWNjSVJ1TTJyWFZyQXpBdmltRDIifQ.HF9C4l0x3Y341Lj_dTkVCCASvbvMgcamBvDJ20GKCmM"
    # "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE4NDc3OTMxMTIsInN1YiI6Ik9ESjlkQnBQMUVTZEl2N0w5Wms4V1pxTkJjMDIifQ.qwy_rH80dRDRJnIQCFCL3ubqKg_E2n8GT2iVNWBBFZw"
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="class")
def create_secteur(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/"
    sector_name = "test"
    response = client.post(
        url,
        headers=HEADERS,
        data={"newlabel": sector_name},
    )
    response_json = response.json()
    
    assert response.status_code == 200
    assert response_json["newlabel"] == sector_name
    return response_json["id"]

@pytest.fixture(scope="class")
def create_spraywall(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/"
    response = client.post(
        url,
        headers=HEADERS,
        files={"image": open("./app/tests/test.jpg", "rb")},
        data={"annotations": [], "label": "test_label"},
    )
    response_json = response.json()
    assert response.status_code == 200
    return response_json

@pytest.fixture(scope="function")
def get_spraywalls(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/"
    response = client.get(
        url,
        headers=HEADERS,
    )
    response_json = response.json()
    assert response.status_code == 200
    return response_json

@pytest.fixture(scope="class")
def create_contest(client):
    blocs = []
    for i in range(1, 30):
        blocs.append({"zones": 2, "numero": i})

    data = {
        "title": "test",
        "description": "test",
        # "image": "test",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "priceE": 10,
        "priceA": 10,
        "blocs": json.dumps(blocs),
        "phases": json.dumps([{
            "numero": 1,
            "startTime": datetime.datetime.now().strftime("%H:%M:%S"),
            "duree": "00:10:00"
        }]),
        "hasFinal": False,
        "doShowResults": True,
        "scoringType": "PPBZ",
        "pointsPerZone": 250,
    }

    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/"
    response = client.post(
        url,
        data=data,
        headers=HEADERS,
    )

    response_json = response.json()
    assert response.status_code == 200
    return response_json

@pytest.fixture(scope="class")
def create_team_contest(request, client, roles=["role1", "role2", "role3"]):
    scoringType = getattr(request, "param", "FIXED")

    mults = [
        [2 if i == j else 0.5 for i in range(len(roles))]
        for j in range(len(roles))
    ]

    blocs = []
    for i in range(1, 30):
        blocs.append({"zones": 2, "numero": i, "multiplicator": mults[i % len(roles)], "points": int(1000 / 30 * (i + 1))})

    data = {
        "title": "test",
        "description": "test",
        "image_url": "test image url",
        "scoringType": scoringType, # FIXED, PPB, PPBZ

        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "priceE": 5,
        "priceA": 10,

        "hasFinal": False,
        "doShowResults": True,
        "pointsPerZone": 250,

        "roles": json.dumps(roles),
        "blocs": json.dumps(blocs),
        "phases": json.dumps([{
            "numero": 1,
            "startTime": datetime.datetime.now().strftime("%H:%M:%S"),
            "duree": "00:10:00"
        }]),
    }

    url = f"/api/v2/climbingLocation/{CLIMBINGLOCATION_ID}/contest/"
    response = client.post(
        url,
        data=data,
        headers=HEADERS,
    )

    response_json = response.json()
    return response_json


@pytest.fixture(scope="class")
def get_location_infos(client):
    url = f"/api/v1/climbingLocation/?climbingLocation_id={CLIMBINGLOCATION_ID}"
    response = client.get(url, headers=HEADERS)
    response_json = response.json()
    assert response.status_code == 200
    return response_json


@pytest.fixture(scope="class")
def get_grade(client, get_location_infos):
    location = get_location_infos
    return location["grades"][0]


@pytest.fixture(scope="function")
def get_walls(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/list-actual-walls/"
    response = client.get(url, headers=HEADERS)
    response_json = response.json()
    assert response.status_code == 200
    return response_json

def generate_tokens(client, start=0, num=10):
    tokens = []

    # try to register N users
    for i in range(start, start + num):
        username = f"testUsername{i}"
        password = "testPassword"
        email = f"test_{i}@votaitest.fr"
        url = "/api/v1/register/"
        try:
            response = client.post(url, data = {"email": email, "password": password, "password2": password, "username": username})
            response_json = response.json()
        except Exception as e:
            print(e)
            continue

    # try to login N users
    for i in range(start, start + num):
        username = f"testUsername{i}"
        password = "testPassword"
        email = f"test_{i}@votaitest.fr"
        url = "/api/v1/login/"

        response = client.post(url, data = {"email": email, "password": password})
        response_json = response.json()
        tokens.append(response_json["access_token"])

    return tokens

@pytest.fixture(scope="class")
def generate_tokens_fixture(client, num_clients=10):
    return generate_tokens(client, 0, num_clients)

@pytest.fixture(scope="class")
def get_token(client):
    password = "testPassword"
    email = "test_0@votaitest.fr"

    url = "/api/v1/login/"
    response = client.post(url, data = {"email": email, "password": password})
    response_json = response.json()
    return response_json["access_token"]


@pytest.fixture(scope="class")
def create_vsl(client):
    data = {
        "vsl": json.dumps({
            "title": "Test VSL",
            "description": "Test VSL Description",
            "start_date": datetime.datetime.now().isoformat(),
            "end_date": (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat(),
            "is_actual": True,
        })
    }

    response = client.post(
        "/api/v1/vsl/",
        headers=HEADERS,
        data=data
    )

    response_json = response.json()
    assert response.status_code == 200
    return response_json

@pytest.fixture(scope="function")
def get_vsl_team(client, create_vsl):
    vsl_id = create_vsl["id"]
    url = f"/api/v1/vsl/{vsl_id}/teams/?climbingLocation_id={CLIMBINGLOCATION_ID}"
    response = client.get(url, headers=HEADERS)
    teams = response.json()
    assert response.status_code == 200
    return teams[0]


@pytest.fixture(scope="function")
def get_contest_teams(client, create_team_contest):
    contest_id = create_team_contest["id"]
    url = f"/api/v1/contest/{contest_id}/teams/"
    response = client.get(url, headers=HEADERS)
    teams = response.json()
    assert response.status_code == 200
    return teams
