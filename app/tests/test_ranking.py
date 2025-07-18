import unittest
import pytest
import datetime
import json
import logging

from .conftest import CLIMBINGLOCATION_ID, HEADERS


# CLIMBINGLOCATION_ID = "6X2xiXVAwXBdfYHB1jYp"

@pytest.mark.skipif(True, reason="Not tested yet")
class TestRanking:
    def test_ranking_global(self, client):
        url = "/api/v1/user/ranking/global/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        assert response.status_code == 200

    def test_ranking_ClimbingLocation(self, client):
        url = f"/api/v1/user/ranking/{CLIMBINGLOCATION_ID}/"
        response = client.get(url, headers=HEADERS)
        response_json = response.json()
        print(len(response_json))
        assert response.status_code == 200
