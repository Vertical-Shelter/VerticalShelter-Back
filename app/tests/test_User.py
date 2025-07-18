import pytest
import datetime
import json
from .conftest import HEADERS, CLIMBINGLOCATION_ID, client

TOKEN = ""

@pytest.mark.skip
def test_register_user_successufl(client):
    url = "/api/v1/register/"
    email = "testing@test.com"
    password = "password"
    password2 = "password"
    username = "testUsername"
    response = client.post(url, data = {"email": email, "password": password, "password2": password2, "username": username})


@pytest.mark.skip
def test_login_user_successfull(client):
    url = "/api/v1/login/"
    email = "testing@test.com"
    password = "password"
    
    response = client.post(url, data = {"email": email, "password": password})
    response_json = response.json()
    assert response_json["access_token"] != None
    assert response_json["refresh_token"] != None
    assert response_json["userId"] != None
    assert response_json["name"] == "testUsername"
    assert response_json["isGym"] == False
    assert response_json["climbingLocation"] == None
    assert response.status_code == 200
    global TOKEN
    TOKEN = response_json["access_token"]
    

@pytest.mark.skip
def test_logout_user_successfull(client):
    url = "/api/v1/logout/"
    header = {"Authorization": f"Bearer {TOKEN}"}
    response = client.post(url, headers=header)
    assert response.status_code == 200
   
    
@pytest.mark.skip
def test_get_profile_successfull(client):
    url = "/api/v1/user/me-new/"
    header = {"Authorization": f"Bearer {TOKEN}"}
    response = client.get(url, headers=header)
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["description"] == ""
    assert response_json["username"] == "testUsername"
    assert response_json["isGym"] == False
    assert response_json["lastDateNews"] == ""
    assert response_json["profile_image_url"] == ""
    
    
    
@pytest.mark.skip
def test_delete_user_successfull(client):
    url = "/api/v1/user/me/"
    header = {"Authorization": f"Bearer {TOKEN}"}
    response = client.delete(url, headers=header)
    assert response.status_code == 200
    

@pytest.mark.skip
def test_update_user_profile_successfull(client):
    url = "/api/v1/user/me/"
    username = "modifiedUsername"
    description = "modifiedDescription"
    climbinglocation_id = CLIMBINGLOCATION_ID

    # only edit username / description
    response = client.patch(url, headers=HEADERS, data = {"username": username, "description": description})
    assert response.status_code == 200
    print(response.json())

    # only edit climbinglocation_id
    response = client.patch(url, headers=HEADERS, data = {"climbingLocation_id": climbinglocation_id})
    assert response.status_code == 200
    print(response.json())

    # no data
    response = client.patch(url, headers=HEADERS)
    assert response.status_code == 200
    print(response.json())
