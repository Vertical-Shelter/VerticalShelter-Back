from .conftest import HEADERS, CLIMBINGLOCATION_ID, client, create_vsl, get_vsl_team, get_token
from ..settings import firestore_async_db

import json
import datetime

class TestVSL:
    def test_create_vsl(self, client, create_vsl):
        response = create_vsl

        assert response["title"] == "Test VSL"
        assert response["description"] == "Test VSL Description"
        assert response["start_date"] is not None
        assert response["end_date"] is not None
        assert response["image_url"] == ""
        assert response["id"] is not None

    def test_get_vsl(self, client, create_vsl):
        vsl_id = create_vsl["id"]

        url = f"/api/v1/vsl/?vsl_id={vsl_id}"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["title"] == "Test VSL"
        # ...

    def test_get_active_vsl(self, client, create_vsl):
        url = "/api/v1/vsl/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["title"] == "Test VSL" or response_json["title"] == "Updated VSL"

    def test_get_vsls(self, client, create_vsl):
        url = "/api/v1/vsls/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert len(response_json) > 0
        assert response_json[0]["title"] == "Test VSL" or response_json[0]["title"] == "Updated VSL"
        # ...

    def test_update_vsl(self, client, create_vsl):
        vsl_id = create_vsl["id"]
        url = f"/api/v1/vsl/{vsl_id}/"

        start_date = datetime.datetime.now(datetime.timezone.utc)
        now_plus_1000_years = start_date + datetime.timedelta(days=365*1001)
        end_4_months_later = now_plus_1000_years + datetime.timedelta(days=31*5)
        end_4_months_later_date = end_4_months_later.strftime("%Y-%m-%d %H:%M:%S")

        data = {
            "vsl": json.dumps({
                "title": "Updated VSL",
                "description": "Updated VSL Description",
                "start_date": start_date.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": end_4_months_later_date,
                "image_url": "https://example.com/image.jpg",
            })
        }
        response = client.put(url, data=data, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["title"] == "Updated VSL"
        # ...    

    class TestLeagues:
        def test_create_league(self, client, create_vsl):
            vsl_id = create_vsl["id"]
            url = f"/api/v1/vsl/{vsl_id}/leagues/"
            data = {
                "climbingLocation_id": CLIMBINGLOCATION_ID,
            }
            response = client.post(url, data=data, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "El Cap"
            # ...

        def test_list_leagues(self, client, create_vsl):
            vsl_id = create_vsl["id"]
            url = f"/api/v1/vsl/{vsl_id}/leagues/"
            response = client.get(url, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert len(response_json) > 0
            assert response_json[0]["name"] == "El Cap"
            # ...

    class TestTeamVSL:
        # def test_create_team(self, client, create_vsl):
        #     vsl_id = create_vsl["id"]
        #     url = f"/api/v1/vsl/{vsl_id}/teams/"
        #     data = {
        #         "team": json.dumps({
        #             "climbingLocation_id": CLIMBINGLOCATION_ID,
        #             "name": "Test Team",
        #             "description": "Test Team Description",
        #             "image_url": "https://example.com/image.jpg",
        #         }),
        #         "inscription": json.dumps({
        #             "first_name": "John",
        #             "last_name": "Doe",
        #             "gender": "M",
        #             "age": 25,
        #             "address": "1 rue de la paix",
        #             "city": "Paris",
        #             "postal_code": "75000",
        #         }),
        #     }
        #     response = client.post(url, data=data, headers=HEADERS)
        #     response_json = response.json()
        #     assert response.status_code == 200
        #     assert response_json["name"] == "Test Team"
        #     # ...

        def test_create_team(self, client, create_vsl):
            vsl_id = create_vsl["id"]
            url = f"/api/v1/vsl/{vsl_id}/teams/"
            data = {
                "team": json.dumps({
                    "climbingLocation_id": CLIMBINGLOCATION_ID,
                    "name": "Test Team",
                    "description": "Test Team Description",
                    "image_url": "https://example.com/image.jpg",
                }),
            }
            response = client.post(url, data=data, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Test Team"
            assert "phase" not in response_json # make sure it's not a contest team
            # ...
        
        def test_then_join(self, client, create_vsl, get_vsl_team):
            vsl_id = create_vsl["id"]
            team_id = get_vsl_team["id"]

            url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/join/"
            data = {
                "inscription": json.dumps({
                    "first_name": "John",
                    "last_name": "Doe",
                    "gender": "M",
                    "age": 25,
                    "address": "1 rue de la paix",
                    "city": "Paris",
                    "postal_code": "75000",
                    "role": "gecko",
                }),
            }
            response = client.post(url, data=data, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Test Team"
            assert len(response_json["members"]) == 1
            # ...

        def test_get_team(self, client, create_vsl, get_vsl_team):
            vsl_id = create_vsl["id"]
            team_id = get_vsl_team["id"]
            url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/"
            response = client.get(url, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Test Team"
            # ...

        def test_get_cloc_teams(self, client, create_vsl):
            vsl_id = create_vsl["id"]
            climbingLocation_id = CLIMBINGLOCATION_ID

            url = f"/api/v1/vsl/{vsl_id}/teams/?climbingLocation_id={climbingLocation_id}"
            response = client.get(url, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert len(response_json) > 0
            assert response_json[0]["name"] == "Test Team" or response_json[0]["name"] == "Updated Team"
            # ...

        def test_update_team(self, client, create_vsl, get_vsl_team):
            vsl_id = create_vsl["id"]
            team_id = get_vsl_team["id"]
            url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/"
            data = {
                "team": json.dumps({
                    "climbingLocation_id": CLIMBINGLOCATION_ID,
                    "name": "Updated Team",
                    "description": "Updated teamDescription",
                    "image_url": "https://example.com/image.jpg",
                })
            }
            response = client.patch(url, data=data, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Updated Team"
            # ...

        def test_update_role_200(self, client, create_vsl, get_vsl_team):
            vsl_id = create_vsl["id"]
            team_id = get_vsl_team["id"]

            url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/role/"
            data = {
                "role": "ninja",
            }
            response = client.patch(url, data=data, headers=HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["roles"]["ninja"] is not None

        def test_someone_else_join(self, client, create_vsl, get_vsl_team, get_token):
            vsl_id = create_vsl["id"]
            team_id = get_vsl_team["id"]

            new_token = get_token
            new_header = {"Authorization": f"Bearer {new_token}"}

            url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/join/"
            data = {
                "inscription": json.dumps({
                    "first_name": "Testeur",
                    "last_name": "Fou",
                    "gender": "M",
                    "age": 42,
                    "address": "2 rue de la paix",
                    "city": "Paris",
                    "postal_code": "75000",
                    "role": "gecko",
                }),
            }
            response = client.post(url, data=data, headers=new_header)
            response_json = response.json()

            assert response.status_code == 200
            assert response_json["name"] == "Updated Team"
            assert len(response_json["members"]) == 2

        def test_sentwall(self, client, get_walls):
            # hopefully this wall exists
            wall_id = get_walls[-1]["id"]
            sector_id = get_walls[-1]["secteur"]["id"]

            url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/sentwall/"
            response = client.post(url, headers=HEADERS)

            # if it's already sent, it should return 400.
            if response.status_code == 400:
                url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/sentwall/"
                response = client.delete(url, headers=HEADERS)
                assert response.status_code == 200

                # resend it
                url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/secteur/{sector_id}/wall/{wall_id}/sentwall/"
                response = client.post(url, headers=HEADERS)

            assert response.status_code == 200

        def test_get_team_history(self, client, create_vsl, get_vsl_team):
            vsl_id = create_vsl["id"]

            url = f"/api/v1/vsl/{vsl_id}/teams/my/"
            response = client.get(url, headers=HEADERS)
            response_json = response.json()

            assert response.status_code == 200
            assert response_json is not None
            assert isinstance(response_json, dict)

            history = response_json.get("history", [])
            assert len(history) >= 0

            for h in history:
                assert h["points"] > 0
                assert h["date"] is not None
                assert h["sentWall"] is not None


    def test_get_league_score(self, client, create_vsl):
        vsl_id = create_vsl["id"]
        url = f"/api/v1/vsl/{vsl_id}/leagues/{CLIMBINGLOCATION_ID}/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json is not None
        assert len(response_json) > 0

        for team in response.json():
            assert team["name"] is not None
            assert team["points"] >= 0 # the sentwall test should have added points

            members = team["members"]
            assert len(members) > 0

            for member in members:
                assert member["username"] is not None
                assert member["points"] >= 0
                assert member["gender"] is not None

    def test_owner_leaves(self, client, create_vsl, get_vsl_team):
        vsl_id = create_vsl["id"]
        team_id = get_vsl_team["id"]

        url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/leave"
        response = client.delete(url, headers=HEADERS)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json is not None

        # make sure that the points of the owner are removed
        url = f"/api/v1/vsl/{vsl_id}/leagues/{CLIMBINGLOCATION_ID}/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json is not None
        assert len(response_json) > 0

        for team in response_json:
            if team["id"] == team_id:
                assert team["points"] == 0
                assert len(team["members"]) == 1
                assert len(team["roles"]) == 1
    
    def test_last_member_leaves(self, client, create_vsl, get_vsl_team, get_token):
        vsl_id = create_vsl["id"]
        team_id = get_vsl_team["id"]

        new_token = get_token
        new_header = {"Authorization": f"Bearer {new_token}"}

        url = f"/api/v1/vsl/{vsl_id}/teams/{team_id}/leave"
        response = client.delete(url, headers=new_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json is None

    def test_get_league_empty(self, client, create_vsl):
        vsl_id = create_vsl["id"]
        url = f"/api/v1/vsl/{vsl_id}/leagues/{CLIMBINGLOCATION_ID}/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json == []

    # @pytest.mark.skip(reason="doesn't work")
    # # do this manually to avoid any problem in production
    # def test_delete_vsl(self, client, create_vsl):
    #     vsl = create_vsl
    #     vsl_id = create_vsl["id"]
    #     assert vsl_id is not None

    #     # can only delete test VSLs from future (+500 years)
    #     # Just in case anything goes wrong with the prod / test environment

    #     start_date = datetime.datetime.fromisoformat(vsl["start_date"])
    #     start_date = start_date.astimezone(datetime.timezone.utc)

    #     assert start_date >= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365*500)

    #     firestore_async_db.collection("vsl").document(vsl_id).delete()
