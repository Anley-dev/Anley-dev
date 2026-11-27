import pytest
import httpx
import sqlite3
import os
import math

BASE_URL = "http://127.0.0.1:8080"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "hawassa_places.db")

@pytest.fixture(scope="session")
def client():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c

def test_database_connected(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["database"]["connected"] is True
    assert data["database"]["place_count"] >= 30
    assert data["routing_engine"]["online"] is True

def test_multilingual_search(client):
    # English search
    r_en = client.get("/api/search", params={"q": "Piazza"})
    assert r_en.status_code == 200
    assert r_en.json()["count"] >= 1

    # Amharic search
    r_am = client.get("/api/search", params={"q": "መናኸሪያ"})
    assert r_am.status_code == 200
    assert r_am.json()["count"] >= 1
    assert "Menharya" in r_am.json()["results"][0]["name"]

def test_nearest_taxi_endpoint(client):
    # Near Hawassa University Main
    res = client.post("/api/nearest-taxi", json={"lat": 7.0531, "lon": 38.4947})
    assert res.status_code == 200
    data = res.json()
    assert "nearest" in data
    assert data["nearest"]["distance_m"] < 100
    assert "Hawassa University" in data["nearest"]["name"]

def test_route_calculation_endpoint(client):
    # Route from Referral Hospital to Piazza
    res = client.post("/api/route", json={
        "start_lat": 7.0458,
        "start_lon": 38.4886,
        "end_lat": 7.0583,
        "end_lon": 38.4720,
        "costing": "auto"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["engine"] == "valhalla"
    assert data["distance_m"] > 1000
    assert data["duration_min"] >= 1
    assert len(data["coordinates"]) > 5
    assert len(data["maneuvers"]) > 0

def test_auth_and_call_logging_flow(client):
    # 1. Login
    login_res = client.post("/api/auth/login", json={"username": "agent1", "password": "agent123"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "agent1"

    # 3. Log a call
    log_res = client.post("/api/calls/log", json={
        "caller_name": "Lake Tourist",
        "caller_lat": 7.0410,
        "caller_lon": 38.4610,
        "dest_name": "Piazza",
        "nearest_station": "Haile Resort Lake Stand",
        "distance_m": 50,
        "travel_mode": "auto",
        "status": "dispatched"
    }, headers=headers)
    assert log_res.status_code == 200
    assert log_res.json()["status"] == "success"

    # 4. Check recent calls & stats
    recent_res = client.get("/api/calls/recent")
    assert recent_res.status_code == 200
    assert len(recent_res.json()["calls"]) >= 1

    stats_res = client.get("/api/calls/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_calls"] >= 1

def test_ai_dispatch_assistant(client):
    res = client.post("/api/ai/dispatch", json={
        "text": "I am standing at Referral Hospital and I want to go to Piazza"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "script_en" in data
    assert "script_am" in data
    assert data["origin"] is not None
    assert data["nearest_station"] is not None
