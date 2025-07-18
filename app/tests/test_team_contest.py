import pytest
import json

from .conftest import CLIMBINGLOCATION_ID, HEADERS, create_team_contest, get_contest_teams, client, generate_tokens

# @pytest.mark.parametrize("create_team_contest", ["PPB", "PPBZ", "FIXED"], indirect=True)
class TestTeamContest:
    """Test contest creation, subscription, and scoring"""	
    def get_contest(self, client, contest_id):
        url = f"/api/v2/climbingLocation/{CLIMBINGLOCATION_ID}/contest/"
        response = client.get(url, headers=HEADERS, params={"contest_id": contest_id})
        response_json = response.json()
        return response_json

    def test_create_team_contest(self, create_team_contest):
        response_json = create_team_contest
        assert response_json["title"] == "test"
        assert response_json["description"] == "test"
        assert response_json["priceE"] == 5 
        assert response_json["priceA"] == 10
        assert response_json["etat"] == -1
        assert response_json["hasFinal"] == False
        assert response_json["scoringType"] in ["PPB", "PPBZ", "FIXED"]

    def test_start_contest(self, client, create_team_contest):
        contest_id = create_team_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/start/"
        response = client.put(url, headers=HEADERS)
        assert response.status_code == 200

    @pytest.mark.parametrize("team_num", range(5))
    class TestCreateTeams:
        def test_create_teams(self, client, create_team_contest, team_num):
            contest = create_team_contest
            contest_id = contest["id"]

            roles = contest["roles"]

            # create the team
            url = f"/api/v1/contest/{contest_id}/teams/"
            data = {
                "team": json.dumps({
                    "climbingLocation_id": CLIMBINGLOCATION_ID,
                    "name": "Test Team",
                    "description": "Test Team Description",
                    "image_url": "https://example.com/image.jpg",
                    "phase": 1,
                }),
            }
            token = generate_tokens(client, team_num * len(roles), 1)[0]
            TMP_HEADERS = HEADERS.copy()
            TMP_HEADERS["Authorization"] = f"Bearer {token}"

            response = client.post(url, data=data, headers=TMP_HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Test Team"
            assert response_json["phase"] == 1

            # then join it
            team_id = response_json["id"]
            url = f"/api/v1/contest/{contest_id}/teams/{team_id}/join/"
            data = {
                "inscription": json.dumps({
                    "first_name": "Test",
                    "last_name": f"User_{team_num}_0",
                    "gender": "M",
                    "age": 25,
                    "address": "1 rue de la paix",
                    "city": "Paris",
                    "postal_code": "75000",
                    "role": roles[0],
                }),
            }
            response = client.post(url, data=data, headers=TMP_HEADERS)
            response_json = response.json()
            assert response.status_code == 200
            assert response_json["name"] == "Test Team"

        def test_fill_teams(self, client, create_team_contest, get_contest_teams, team_num):
            contest = create_team_contest
            contest_id = contest["id"]

            teams = get_contest_teams
            team_id = teams[team_num]["id"]

            roles = contest["roles"]

            url = f"/api/v1/contest/{contest_id}/teams/{team_id}/join/"
            
            # slot 1 is already filled
            tokens = generate_tokens(client, team_num * len(roles) + 1, len(roles) - 1)
            for i in range(1, len(roles)):
                TMP_HEADERS = HEADERS.copy()
                TMP_HEADERS["Authorization"] = f"Bearer {tokens[i - 1]}"

                data = {
                    "inscription": json.dumps({
                        "first_name": "Test",
                        "last_name": f"User_{team_num}_{i}",
                        "gender": "M" if i % 2 == 0 else "F",
                        "age": 25 if (team_num + i) % 3 != 0 else 16,
                        "address": "1 rue de la paix",
                        "city": "Paris",
                        "postal_code": "75000",
                        "role": roles[i],
                    }),
                }

                response = client.post(url, data=data, headers=TMP_HEADERS)
                response_json = response.json()
                assert response.status_code == 200
                assert response_json["name"] == "Test Team"

        def test_scoring_contest(self, client, create_team_contest, team_num):
            contest = create_team_contest
            contest_id = contest["id"]

            url = f"/api/v2/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/score/"
            tokens = generate_tokens(client, team_num * len(contest["roles"]), len(contest["roles"]))

            for i in range(len(contest["roles"])):
                TMP_HEADERS = HEADERS.copy()
                TMP_HEADERS["Authorization"] = f"Bearer {tokens[i]}"

                blocs = [(int(i % 2 == 0) * 2) - 1 for i in range(len(contest["blocs"]))]
                data = {"score": json.dumps(blocs)}

                response = client.post(url, data=data, headers=TMP_HEADERS)
                assert response.status_code == 200
                assert response.json()["message"] == "Score added successfully"

            assert len(contest["roles"]) > 0 # just in case

    def test_get_contest_score(self, client, create_team_contest):
        contest = create_team_contest
        contest_id = contest["id"]

        url = f"/api/v2/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/score/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert isinstance(response_json, list)
        assert len(response_json) > 0

        # there should be at least some points in every teams
        for team in response_json:
            assert team["points"] > 0

        # test filters ["Homme", "Femme", "Jeune", "Mixte"]
        for f in ["Homme", "Femme", "Jeune", "Mixte"]:
            response = client.get(url, headers=HEADERS, params={"filter": f})
            response_json = response.json()
            assert response.status_code == 200
            assert isinstance(response_json, list)
            assert len(response_json) >= 0


    """ Stop contest """
    def test_stop_contest(self, client, create_team_contest):
        contest_id = create_team_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/end/"
        response = client.put(url, headers=HEADERS)
        assert response.status_code == 200

    def test_get_contest_ended(self, client, create_team_contest):
        response_json = self.get_contest(client, create_team_contest["id"])
        assert response_json["etat"] == 1 # ended
