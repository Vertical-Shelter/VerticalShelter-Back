import pytest

from .conftest import CLIMBINGLOCATION_ID, HEADERS, client, create_secteur


class TestStatsOld:
    def test_get_user_history(self, client):
        url = "/api/v1/user/me/history-new/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200
        assert len(response_json) > 0

    def test_get_user_stats_global(self, client):
        url = "/api/v1/user/me/stats/global/"
        response = client.get(url, headers=HEADERS, params={"filter_by": "week"})
        assert response.status_code == 200

    def test_get_stats_per_gym(self, client):
        url = "/api/v1/user/me/stats/perGym/"
        response = client.get(url, headers=HEADERS, params={"filter_by": "week"})
        assert response.status_code == 200

class TestStatsNew:
    def test_get_user_history(self, client):
        url = "/api/v1/stats/user/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200

        assert len(response_json) > 0

        for cloc_stats in response_json:
            assert "count_sentwalls" in cloc_stats
            assert "count_attributes" in cloc_stats
            assert "count_grades" in cloc_stats
            assert "sessions" in cloc_stats

    def test_get_ouvreur_stats(self, client):
        url = f"/api/v1/stats/ouvreur/"
        response = client.get(url, headers=HEADERS, params={"climbingLocation_id": CLIMBINGLOCATION_ID})
        response_json = response.json()
        assert response.status_code == 200

        assert isinstance(response_json, list) and len(response_json) > 0
        for wall_stats in response_json:
            assert "count_sentwalls" in wall_stats
            assert "sentwalls" in wall_stats
            assert "secteur_id" in wall_stats
            assert "date" in wall_stats