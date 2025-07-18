import datetime
import pytest
import json

from .conftest import CLIMBINGLOCATION_ID, HEADERS, create_contest, client

NB_INSCRIPTIONS = 20

class TestContest:
    """Test contest creation, subscription, and scoring"""	

    def get_contest(self, client, contest_id):
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/"
        response = client.get(url, headers=HEADERS, params={"contest_id": contest_id})
        response_json = response.json()
        return response_json

    def test_create_contest(self, create_contest):
        response_json = create_contest
        assert response_json["title"] == "test"
        assert response_json["description"] == "test"
        assert response_json["priceE"] == 10
        assert response_json["priceA"] == 10
        assert response_json["etat"] == -1
        assert response_json["hasFinal"] == False

    def test_start_contest(self, client, create_contest):
        contest_id = create_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/start/"
        response = client.put(url, headers=HEADERS)
        assert response.status_code == 200
  
    def test_subscribe_contest_user(self, client, create_contest):
        contest_resp = create_contest
        contest_id = contest_resp["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/inscription/"

        for i in range(2):
            data = {
                "genre": "M",
                "nom": "test_" + str(i),
                "prenom": "test" + str(i),
                "isMember": True,
                "phaseId": contest_resp["phases"][0]["id"],
                "is18YO": True,
            }

            response = client.post(url, data=data, headers=HEADERS)
            assert response.status_code == 200

        updated_contest = self.get_contest(client, contest_id)
        assert len(updated_contest["inscriptionList"]) == 1

    @pytest.mark.skip(reason="QR code confirmation does not exist anymore")
    def test_scoring_user(self, client, create_contest):
        contest_resp = self.get_contest(client, create_contest["id"])
        contest_id = contest_resp["id"]
        assert contest_id == create_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/score/"

        blocs = []
        for j in range(len(contest_resp["blocs"])):
            zones_test = [
                [False, False],
                [True, False],
                [True, True],
                [True, True], # succeed
            ]

            blocs.append({
                "blocId": contest_resp["blocs"][j]["id"],
                "isSucceed": j % 4 == 3,
                "isZoneSucceed": zones_test[j % 4],
            })


        data = {
            "score": json.dumps(blocs),
            # no need for inscription id
        }

        response = client.post(url, data=data, headers=HEADERS)
        assert response.status_code == 200
        # will not score because QR code has not been scanned
        assert response.json()["message"] == "QR code not scanned"

    def test_subscribe_contest_guest(self, client, create_contest):
        contest_resp = create_contest
        contest_id = contest_resp["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/inscription-guest/"

        for i in range(NB_INSCRIPTIONS):
            data = {
                "genre": i % 2 == 0 and "M" or "F",
                "nom": "test_" + str(i),
                "prenom": "test" + str(i),
                "isMember": False,
                "phaseId": contest_resp["phases"][0]["id"],
                "is18YO": True,
                "isGuest": True,
            }

            response = client.post(url, data=data, headers=HEADERS)
            assert response.status_code == 200

        updated_contest = self.get_contest(client, contest_id)
        assert len(updated_contest["inscriptionList"]) == NB_INSCRIPTIONS + 1

    def test_scoring_guest(self, client, create_contest):
        contest_resp = self.get_contest(client, create_contest["id"])
        contest_id = contest_resp["id"]
        assert contest_id == create_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/score-guest/"

        def get_random_blocs(i):
            """Test score"""
            if contest_resp["inscriptionList"][i].get("isMember"):
                return

            blocs = []
            for j in range(len(contest_resp["blocs"])):
                zones_test = [
                    [False, False],
                    [True, False],
                    [True, True],
                    [True, True], # succeed
                ]

                blocs.append({
                    "blocId": contest_resp["blocs"][j]["id"],
                    "isSucceed": j % 4 == 3,
                    "isZoneSucceed": zones_test[j % 4],
                })

            data = {
                "score": json.dumps(blocs),
                "inscription_id": contest_resp["inscriptionList"][i]["id"],
            }

            response = client.post(url, data=data, headers=HEADERS)
            assert response.status_code == 200
            assert response.json()["message"] == "Score added successfully"

        num_inscriptions = len(contest_resp["inscriptionList"])

        for i in range(num_inscriptions):
            get_random_blocs(i)

    def test_get_score_gym(self, client, create_contest):
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{create_contest["id"]}/resultat/"
        response = client.get(url, headers=HEADERS, params={"filter": "global"})
        assert response.status_code == 200
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == NB_INSCRIPTIONS + 1
        assert response_json[0]["points"] > 0 # at least someone has scored


    def test_get_score_user(self, client, create_contest):
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{create_contest["id"]}/resultat-user/"

        # global
        response = client.get(url, headers=HEADERS, params={"filter": "global"})
        assert response.status_code == 200
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == NB_INSCRIPTIONS + 1

        # men
        response = client.get(url, headers=HEADERS, params={"filter": "M"})
        assert response.status_code == 200
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == (NB_INSCRIPTIONS / 2) + 1

        # women
        response = client.get(url, headers=HEADERS, params={"filter": "F"})
        assert response.status_code == 200
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == (NB_INSCRIPTIONS / 2)

        # no filter (global)
        response = client.get(url, headers=HEADERS)
        assert response.status_code == 200
        response_json = response.json()
        assert isinstance(response_json, list)
        assert len(response_json) == NB_INSCRIPTIONS + 1

    def test_get_contest(self, client, create_contest):
        response_json = self.get_contest(client, create_contest["id"])
        assert response_json["title"] == "test"
        assert response_json["description"] == "test"
        assert response_json["priceE"] == 10
        assert response_json["priceA"] == 10
        assert response_json["etat"] == 0 # ongoing
        assert response_json["hasFinal"] == False

    def test_get_contest_less18(self, client, create_contest):
        contest_resp = create_contest
        contest_id = contest_resp["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/resultat-less18/"

        response = client.get(url, headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == {"global": [], "M": [], "F": []} # there shoulde be not < 18

    def test_patch_phases(self, client, create_contest):
        contest_resp = create_contest
        contest_id = contest_resp["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/?contest_id={contest_id}"

        data = {
            "phases": json.dumps([
                {
                    "numero": 1,
                    "startTime": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "duree": "00:30:00", # 30 minutes
                }
            ])
        }

        response = client.patch(url, data=data, headers=HEADERS)
        assert response.status_code == 200

        # check that the contest can still be retrieved + the inscriptions are not buggy
        updated_contest = self.get_contest(client, contest_id)
        assert len(updated_contest["phases"]) == 1
        assert len(updated_contest["inscriptionList"]) >= 1

       
    """ Stop contest """
    def test_stop_contest(self, client, create_contest):
        contest_id = create_contest["id"]
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/contest/{contest_id}/end/"
        response = client.put(url, headers=HEADERS)
        assert response.status_code == 200

    def test_get_contest_ended(self, client, create_contest):
        response_json = self.get_contest(client, create_contest["id"])
        assert response_json["etat"] == 1 # ended


    # def test_delete_contest(self, client):
    #     url = "/api/v1/climbingLocation/" + climbingLocation_id + "/contest/" + contest_resp["id"] + "/"
    #     response = client.delete(url, headers = headers)
    #     assert response.status_code == 200
    #     # Further assertions to check Firestore writes or storage uploads can be added.


    # def test_get_climbinlocation(self, client):
    #     response = client.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat/")
    #     assert response.status_code == 200
    #     # Further assertions to check Firestore writes or storage uploads can be added.

    # def test_get_climbinlocation(self, client):
    #     response = client.get("/api/v1/climbingLocation/{climbingLocation_id}/contest/{contest_id}/resultat-user/")
    #     assert response.status_code == 200
    #     # Further assertions to check Firestore writes or storage uploads can be added.
