import os
import pytest
from starlette.testclient import TestClient

from web_app import app, init_db

@pytest.fixture(scope="session")
def client():
    # Initialize DB schema & default credentials
    init_db()
    with TestClient(app) as c:
        yield c

def test_healthcheck_and_security_headers(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    # Verify security headers
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "SAMEORIGIN"

def test_database_connected(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["database"]["connected"] is True
    assert data["database"]["place_count"] >= 30

def test_multilingual_search(client):
    # English search
    r_en = client.get("/api/search", params={"q": "Piazza"})
    assert r_en.status_code == 200
    assert r_en.json()["count"] >= 1

    # Amharic search
    r_am = client.get("/api/search", params={"q": "መናኸሪያ"})
    assert r_am.status_code == 200
    assert r_am.json()["count"] >= 1
    assert any("Menharya" in p["name"] for p in r_am.json()["results"])

def test_nearest_taxi_endpoint(client):
    # Coordinates near Hawassa University Main Campus
    res = client.post("/api/nearest-taxi", json={"lat": 7.0531, "lon": 38.4947})
    assert res.status_code == 200
    data = res.json()
    assert "nearest" in data
    assert data["nearest"]["distance_m"] < 150
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
    assert data["engine"] in ["valhalla", "fallback_haversine"]
    assert data["distance_m"] > 1000
    assert data["duration_min"] >= 1
    assert len(data["coordinates"]) >= 2
    assert len(data["maneuvers"]) > 0

def test_auth_and_call_logging_flow(client):
    # 1. Invalid login should be rejected with 401
    bad_login = client.post("/api/auth/login", json={"username": "agent1", "password": "wrongpassword"})
    assert bad_login.status_code == 401

    # 2. Valid login
    login_res = client.post("/api/auth/login", json={"username": "agent1", "password": "agent123"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    assert len(token) == 64  # 32-byte hex token
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "agent1"

    # 4. Log a call
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

    # 5. Check recent calls & stats
    recent_res = client.get("/api/calls/recent")
    assert recent_res.status_code == 200
    assert len(recent_res.json()["calls"]) >= 1

    stats_res = client.get("/api/calls/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_calls"] >= 1

def test_protected_place_creation(client):
    test_place_name = "Automated Test Station"
    new_place_data = {
        "name": test_place_name,
        "name_am": "የሙከራ ታክሲ ጣቢያ",
        "latitude": 7.0500,
        "longitude": 38.4800,
        "category": "taxi_station"
    }

    # Unauthenticated attempt should fail with 401
    unauth_res = client.post("/api/places", json=new_place_data)
    assert unauth_res.status_code == 401

    # Authenticated attempt should succeed
    login_res = client.post("/api/auth/login", json={"username": "agent1", "password": "agent123"})
    token = login_res.json()["token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    try:
        auth_res = client.post("/api/places", json=new_place_data, headers=auth_headers)
        assert auth_res.status_code == 200
        assert auth_res.json()["status"] == "success"
    finally:
        # Cleanup test place from DB
        from web_app import get_db_connection
        conn = get_db_connection()
        conn.execute("DELETE FROM places WHERE name = ?", (test_place_name,))
        conn.commit()
        conn.close()

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
