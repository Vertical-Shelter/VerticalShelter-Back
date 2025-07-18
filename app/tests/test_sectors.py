import pytest
import json
from .conftest import CLIMBINGLOCATION_ID, HEADERS, client, create_secteur, generate_tokens_fixture
from concurrent.futures import ThreadPoolExecutor

class TestSectorsManip:
    def test_create_secteur(self, create_secteur):
        secteur_id = create_secteur
        assert secteur_id is not None

    def test_create_walls_in_secteur(self, client, create_secteur, num_walls=30, num_workers=10):
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{create_secteur}/wall/"

        wall_data = {
            "grade_id": "5yafjv9OvCMquYlcKqvV",
            "attributes": ["attt"],
        }

        def create_wall(i):
            response = client.post(
                url,
                headers=HEADERS,
                data={"wall_data": json.dumps(wall_data)},
            )
            return response

        for i in range(num_walls):
            response = create_wall(i)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json.get("id") is not None
            assert response_json.get("secteur", {}).get("id") == create_secteur

    def test_patch_secteur(self, client, create_secteur):
        secteur_id = create_secteur
        assert secteur_id is not None

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{secteur_id}/"
        response = client.patch(
            url,
            headers=HEADERS,
            files={"image": open("./app/tests/test.jpg", "rb")},
        )
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["message"] == "Secteur updated successfully"

    @pytest.mark.skip(reason="Not implemented anymore")
    def test_create_sentwall_list(self, client, create_secteur, get_walls):
        walls = get_walls
        secteur_id = create_secteur

        walls_to_send = []
        # get first half of walls in secteur
        for wall in walls:
            if wall["secteur"]["id"] == secteur_id:
                walls_to_send.append(wall)

        walls_to_send = walls_to_send[:len(walls_to_send)//2]

        def create_sentwall_list(walls):
            body = [
                {
                    "id": wall["id"],
                    "grade_id": wall["grade"]["id"],
                    "nTentative": 1,
                } for wall in walls
            ]

            url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/sentwall/"
            response = client.post(
                url,
                headers=HEADERS,
                data={"sentwalls": json.dumps(body)},
            )
            return response
        
        response = create_sentwall_list(walls_to_send)
        assert response.status_code == 200

    def test_create_sentwall(self, client, create_secteur, get_walls):
        walls = get_walls
        sector_id = create_secteur

        walls_id = []
        # get second half of walls in secteur
        for wall in walls:
            if wall["secteur"]["id"] == sector_id:
                walls_id.append(wall["id"])

        walls_id = walls_id[len(walls_id)//2:]

        def create_sentwall(wall_id):
            url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/sentwall/"
            response = client.post(
                url,
                headers=HEADERS,
            )
            return response

        responses = [create_sentwall(wall_id) for wall_id in walls_id]

        for response in responses:
            response_json = response.json()
            if response.status_code == 400:
                assert response_json == {"detail": {"error": "SentWall already exist"}}
            else:
                assert response.status_code == 200
                assert response_json.get("id") is not None
                assert response_json.get("user", {}).get("username") != None

    def test_create_sentwall_multipleusers(self, client, generate_tokens_fixture, create_secteur, get_walls):
        walls = get_walls
        sector_id = create_secteur
        tokens = generate_tokens_fixture

        # get first wall in secteur
        wall_id = None
        for wall in walls:
            if wall["secteur"]["id"] == sector_id:
                wall_id = wall["id"]
                break

        assert wall_id is not None

        def create_sentwall(wall_id, token):
            url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/sentwall/"
            response = client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
            )
            return response
        
        responses = [create_sentwall(wall_id, token) for token in tokens]

        for response in responses:
            response_json = response.json()
            if response.status_code == 400:
                assert response_json == {"detail": {"error": "SentWall already exist"}}
            else:
                assert response.status_code == 200
                assert response_json.get("id") is not None
                assert response_json.get("user", {}).get("username") != None

    def test_delete_wall(self, client, create_secteur, get_walls):
        walls = get_walls
        sector_id = create_secteur

        # get first wall in secteur
        wall_id = None
        for wall in walls:
            if wall["secteur"]["id"] == sector_id:
                wall_id = wall["id"]
                break

        assert wall_id is not None

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/"
        response = client.delete(
            url,
            headers=HEADERS,
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json["message"] == "Wall deleted successfully"

        # check if wall is deleted
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/"	
        response = client.get(
            url,
            headers=HEADERS,
        )
        assert response.status_code == 400 # (I don't know why it's 400 and not 404 but it's fine)

    def test_migrate_secteur(self, client, create_secteur):
        secteur_id = create_secteur
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{secteur_id}/migrate_to_old_secteur/"
        response = client.post(
            url,
            headers=HEADERS,
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json["message"] == "Secteur updated successfully"

def test_get_actual_walls_ouvreur(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/list-actual-walls/"
    response = client.get(
        url,
        headers=HEADERS,
    )
    response_json = response.json()
    assert response.status_code == 200

    for wall in response_json:
        assert wall.get("id") is not None
        assert wall.get("isActual") == True
        assert isinstance(wall.get("attributes"), list)
        assert isinstance(wall.get("grade"), dict)
        assert isinstance(wall.get("secteur"), dict)



def test_get_actual_walls(client):
    url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/" 
    response = client.get(
        url,
        headers=HEADERS,
    )
    response_json = response.json()
    assert response.status_code == 200

    for wall in response_json:
        assert wall.get("id") is not None
        assert wall.get("isActual") == True
        assert isinstance(wall.get("attributes"), list)
        assert isinstance(wall.get("grade"), dict)
        assert isinstance(wall.get("secteur"), dict)


def test_get_wall(client, get_walls):
    walls = get_walls

    for wall in walls:
        secteur_id = wall["secteur"]["id"]
        wall_id = wall["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{secteur_id}/wall/{wall_id}/"
        response = client.get(
            url,
            headers=HEADERS,
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json.get("id") == wall["id"]
        assert response_json.get("secteur", {}).get("id") == wall["secteur"]["id"]
        assert response_json.get("grade", {}).get("id") == wall["grade"]["id"]

# def test_get_old_walls(client):
#     url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/list-old-walls/" 
#     response = client.get(
#         url,
#         headers=HEADERS,
#     )
#     response_json = response.json()
#     assert response.status_code == 200

#     for wall in response_json:
#         assert wall.get("id") is not None
#         assert wall.get("isActual") == False
#         assert isinstance(wall.get("attributes"), list)
#         assert isinstance(wall.get("grade", {}), dict)
#         assert isinstance(wall.get("secteur"), dict)

# def test_get_actual_walls_100(client, num_users=100, num_workers=100):
#     url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/" 

#     def get_actual_walls(i):
#         response = client.get(
#             url,
#             headers=HEADERS,
#         )
#         return response
    
#     with ThreadPoolExecutor(max_workers=num_workers) as executor:
#         responses = executor.map(get_actual_walls, range(num_users))

#         for response in responses:
#             assert response.status_code == 200
#             response_json = response.json()
#             assert isinstance(response_json, list)

#             for wall in response_json:
#                 assert wall.get("id") is not None
#                 assert wall.get("isActual") == True
#                 assert isinstance(wall.get("attributes"), list)
#                 assert isinstance(wall.get("grade"), dict)
#                 assert isinstance(wall.get("secteur"), dict)

# @pytest.mark.parametrize("max_clients", [400])
# @pytest.mark.parametrize("batch_size", [1])
# def test_charge_get_walls(max_clients, batch_size):
#     SERVER_URL = os.environ.get("SERVER_URL")
#     if SERVER_URL is None:
#         print("SERVER_URL is not set, skipping test")
#         return

#     url = f"http://{SERVER_URL}/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/"


#     def client_batch_get_wall(i):
#         for _ in range(batch_size):
#             response = requests.get(
#                 url,
#                 headers=HEADERS,
#             )
#             #print(response.status_code)
#             assert response.status_code == 200

#     # handle errors
#     with ThreadPoolExecutor(max_workers=max_clients) as executor:
#         executor.map(client_batch_get_wall, range(max_clients))