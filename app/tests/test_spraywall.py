import pytest
import json
from .conftest import CLIMBINGLOCATION_ID, HEADERS, client, create_spraywall, get_spraywalls

class TestSprayWall:
    def get_blocs(self, client, spraywall_id):
        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert isinstance(response_json, list) and len(response_json) > 0

        blocs = response_json
        for bloc in blocs:
            assert bloc.get("id") is not None

        return blocs

    def test_create_spraywall(self, create_spraywall):
        assert create_spraywall is not None

    def test_patch_spraywall_all(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]
        old_image = spraywall["image"]

        annotations = [{
            "id": "42",
            "category_id": 0,
            "segmentation": [0, 0, 0, 1, 0.5, 1],
            "bbox": [0, 0, 1, 1],
            "area" : 0.0,
        }]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/"
        response = client.patch(
            url,
            headers=HEADERS,
            files={"image": open("./app/tests/test.jpg", "rb")},
            data={"annotations": json.dumps(annotations), "label": "test_label_patched"},
        )

        response_json = response.json()
        assert response.status_code == 200
        assert response_json["id"] == spraywall_id
        annotation = response_json["annotations"][0]
        assert all([annotation.get(key) == value for key, value in annotations[0].items()])
        #assert response_json["image"] != old_image # kinda wrong because we use the same image so it's the same url
        assert response_json["label"] == "test_label_patched"

    def test_patch_spraywall_annotations(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]

        annotations = [{
            "id": "42",
            "category_id": 0,
            "segmentation": [0, 0, 0, 1, 0.5, 1],
            "bbox": [0, 0, 1, 1],
            "area" : 0.0,
        }]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/"
        response = client.patch(
            url,
            headers=HEADERS,
            data={"annotations": json.dumps(annotations)},
        )

        response_json = response.json()
        annotation = response_json["annotations"][0]
        assert all([annotation.get(key) == value for key, value in annotations[0].items()])

    def test_get_spraywall_by_label(self, client, create_spraywall):
        spraywall = create_spraywall
        label = "test_label_patched"

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/label/{label}"
        response = client.get(url, headers=HEADERS)
        assert response.status_code == 200

    def test_list_all_spraywalls(self, client, create_spraywall):
        assert create_spraywall is not None # ensure we have at least one spraywall

        url = f"/api/v1/climbingLocation/spraywalls/"
        response = client.get(
            url,
            headers=HEADERS,
        )

        response_json = response.json()
        assert response.status_code == 200
        assert isinstance(response_json, list) and len(response_json) > 0

    def test_get_spraywalls(self, client, create_spraywall, get_spraywalls):
        assert create_spraywall is not None # ensure we have at least one spraywall
        assert get_spraywalls is not None
        assert isinstance(get_spraywalls, list) and len(get_spraywalls) > 0

    def test_get_spraywall(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["id"] == spraywall_id

    def test_create_spraywall_bloc(self, client, create_spraywall, get_grade):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]
        grade_id = get_grade["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/"
        response = client.post(
            url,
            headers=HEADERS,
            data={
                "spraywall_bloc": json.dumps({
                    "description": "test",
                    "grade_id": grade_id,
                    "holds": [{"id": "42", "type": 0}],
                })
            },	
        )
        response_json = response.json()
        assert response.status_code == 200
        assert response_json.get("id") is not None
        assert response_json["date"] is not None

    def test_create_spraywall_bloc_grade_not_found(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/"
        response = client.post(
            url,
            headers=HEADERS,
            data={
                "spraywall_bloc": json.dumps({
                    "description": "test",
                    "grade_id": "42",
                    "holds": [{"id": "42", "type": 0}],
                })
            },	
        )
        response_json = response.json()
        assert response.status_code == 404
        assert response_json == {"detail": "Grade not found"}

    def test_get_spraywall_blocs(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert isinstance(response_json, list) and len(response_json) > 0

        blocs = response_json
        for bloc in blocs:
            assert bloc.get("id") is not None

        bloc_id = blocs[0]["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/{bloc_id}/sentwall/"
        response = client.post(
            url,
            headers=HEADERS,
            data={
                "nTentative": 1,
                "grade_id": "42",
            }
        )
        assert response.status_code == 200
        response_json = response.json()
        assert response_json["id"] is not None
        assert response_json["nTentative"] >= 0

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/{bloc_id}"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["id"] == bloc_id
        assert response_json["description"] == "test"
        assert response_json["date"] is not None
        assert len(response_json["holds"]) > 0
        assert isinstance(response_json["holds"][0], dict)
        assert isinstance(response_json["routesetter"], dict)
        assert len(response_json["sentWalls"]) > 0

        for sentwall in response_json["sentWalls"]:
            assert isinstance(sentwall, dict)
            assert sentwall.get("id") is not None
            assert sentwall.get("date") is not None
            assert isinstance(sentwall.get("user"), dict)

    def test_delete_spraywall_blocs(self, client, create_spraywall):
        spraywall_id = create_spraywall["id"]
        blocs_to_delete = self.get_blocs(client, spraywall_id)

        for blocs in blocs_to_delete:
            bloc_id = blocs["id"]
            url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}/blocs/{bloc_id}"
            response = client.delete(url, headers=HEADERS)
            assert response.status_code == 200
            assert response.json() == {"message": "Bloc deleted successfully"}

    def test_delete_spraywall(self, client, create_spraywall):
        spraywall = create_spraywall
        spraywall_id = spraywall["id"]

        url = f"/api/v1/climbingLocation/{CLIMBINGLOCATION_ID}/spraywalls/{spraywall_id}"
        response = client.delete(url, headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == {"message": "Spraywall deleted successfully"}
