import os
import re
import json
import sqlite3
import math
import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from typing import Optional, List

import httpx
from fastapi import FastAPI, HTTPException, Header, Query, Depends, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "places.csv")
VALHALLA_URL = os.getenv("VALHALLA_URL", "http://localhost:8002")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

http_client: Optional[httpx.AsyncClient] = None

# ==========================================
# In-Memory Rate Limiter Middleware
# ==========================================
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 120    # requests per window
request_counters = defaultdict(list)

# ==========================================
# Database Initialization (Auth & Call Logs)
# ==========================================
def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return hashed, salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    test_hash, _ = hash_password(password, salt)
    return test_hash == password_hash

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'agent',
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_sessions (
        token TEXT PRIMARY KEY,
        agent_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        agent_username TEXT NOT NULL,
        caller_name TEXT,
        caller_lat REAL NOT NULL,
        caller_lon REAL NOT NULL,
        dest_name TEXT,
        dest_lat REAL,
        dest_lon REAL,
        nearest_station TEXT,
        distance_m INTEGER,
        duration_min INTEGER,
        travel_mode TEXT DEFAULT 'auto',
        status TEXT DEFAULT 'dispatched',
        notes TEXT
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM agents")
    if cursor.fetchone()[0] == 0:
        h1, s1 = hash_password("admin123")
        cursor.execute("""
            INSERT INTO agents (username, password_hash, salt, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("admin", h1, s1, "Supervisor Admin", "supervisor", datetime.utcnow().isoformat()))

        h2, s2 = hash_password("agent123")
        cursor.execute("""
            INSERT INTO agents (username, password_hash, salt, full_name, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("agent1", h2, s2, "Hawassa Agent 1", "agent", datetime.utcnow().isoformat()))

    conn.commit()
    conn.close()

# Lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    global http_client
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=2.0, read=15.0, write=5.0, pool=10.0),
        limits=httpx.Limits(max_keepalive_connections=30, max_connections=100)
    )
    yield
    if http_client:
        await http_client.aclose()

app = FastAPI(title="Hawassa Call Center Navigation Web", lifespan=lifespan)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only rate-limit API calls
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        timestamps = request_counters[client_ip]
        # Keep only timestamps within window
        request_counters[client_ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]

        if len(request_counters[client_ip]) >= RATE_LIMIT_MAX:
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please slow down."})

        request_counters[client_ip].append(now)

    response = await call_next(request)
    return response

# ==========================================
# Authentication Helpers
# ==========================================
def get_current_agent(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT agent_id, username, full_name, role, expires_at 
        FROM agent_sessions 
        WHERE token = ?
    """, (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    expires_at = datetime.fromisoformat(row[4])
    if datetime.utcnow() > expires_at:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "full_name": row[2],
        "role": row[3],
        "token": token
    }

# ==========================================
# Pydantic Schemas
# ==========================================
class LoginRequest(BaseModel):
    username: str
    password: str

class NearestRequest(BaseModel):
    lat: float
    lon: float
    category_filter: Optional[str] = "taxi_station"

class PlaceCreateRequest(BaseModel):
    name: str
    name_am: Optional[str] = ""
    name_sid: Optional[str] = ""
    aliases: Optional[str] = ""
    category: Optional[str] = "taxi_station"
    latitude: float
    longitude: float
    description: Optional[str] = ""
    notes: Optional[str] = ""

class RouteRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    costing: Optional[str] = "auto"  # pedestrian, auto, bicycle

class CallLogRequest(BaseModel):
    caller_name: Optional[str] = ""
    caller_lat: float
    caller_lon: float
    dest_name: Optional[str] = ""
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    nearest_station: str
    distance_m: int
    duration_min: Optional[int] = 1
    travel_mode: Optional[str] = "auto"
    status: Optional[str] = "dispatched"
    notes: Optional[str] = ""

class AIDispatchRequest(BaseModel):
    text: str

# ==========================================
# Database Helpers for Places & POIs
# ==========================================
def get_db_places(category: Optional[str] = None):
    if not os.path.exists(DB_PATH):
        return []
    conn = get_db_connection()
    cursor = conn.cursor()
    if category:
        cursor.execute("""
            SELECT id, name, name_am, name_sid, aliases, category, latitude, longitude, description, notes 
            FROM places WHERE category = ? ORDER BY name ASC
        """, (category,))
    else:
        cursor.execute("""
            SELECT id, name, name_am, name_sid, aliases, category, latitude, longitude, description, notes 
            FROM places ORDER BY category DESC, name ASC
        """)
    rows = cursor.fetchall()
    conn.close()

    places = []
    for r in rows:
        places.append({
            "id": r[0],
            "name": r[1],
            "name_am": r[2] or "",
            "name_sid": r[3] or "",
            "aliases": r[4] or "",
            "category": r[5] or "taxi_station",
            "lat": float(r[6]),
            "lon": float(r[7]),
            "description": r[8] or "",
            "notes": r[9] or ""
        })
    return places

def search_db_places(query: str):
    if not os.path.exists(DB_PATH) or not query.strip():
        return []

    q = query.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []

    try:
        fts_query = f'"{q}"*'
        cursor.execute("""
            SELECT p.id, p.name, p.name_am, p.name_sid, p.aliases, p.category, p.latitude, p.longitude, p.description, p.notes
            FROM places_fts f
            JOIN places p ON f.rowid = p.id
            WHERE places_fts MATCH ?
            LIMIT 15
        """, (fts_query,))
        rows = cursor.fetchall()
        for r in rows:
            results.append({
                "id": r[0],
                "name": r[1],
                "name_am": r[2] or "",
                "name_sid": r[3] or "",
                "aliases": r[4] or "",
                "category": r[5] or "",
                "lat": float(r[6]),
                "lon": float(r[7]),
                "description": r[8] or "",
                "notes": r[9] or ""
            })
    except Exception:
        pass

    if not results:
        like_term = f"%{q}%"
        cursor.execute("""
            SELECT id, name, name_am, name_sid, aliases, category, latitude, longitude, description, notes
            FROM places
            WHERE name LIKE ? OR name_am LIKE ? OR name_sid LIKE ? OR aliases LIKE ? OR description LIKE ?
            LIMIT 15
        """, (like_term, like_term, like_term, like_term, like_term))
        rows = cursor.fetchall()
        for r in rows:
            results.append({
                "id": r[0],
                "name": r[1],
                "name_am": r[2] or "",
                "name_sid": r[3] or "",
                "aliases": r[4] or "",
                "category": r[5] or "",
                "lat": float(r[6]),
                "lon": float(r[7]),
                "description": r[8] or "",
                "notes": r[9] or ""
            })

    conn.close()
    return results

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def decode_polyline(polyline_str, precision=6):
    factor = 1.0 / (10 ** precision)
    coordinates = []
    index = 0
    lat = 0
    lng = 0
    length = len(polyline_str)

    while index < length:
        result = 0
        shift = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        result = 0
        shift = 0
        while True:
            b = ord(polyline_str[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        coordinates.append([lat * factor, lng * factor])

    return coordinates

# ==========================================
# Auth API Endpoints
# ==========================================
@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, password_hash, salt, full_name, role 
        FROM agents 
        WHERE username = ?
    """, (req.username.strip(),))
    agent = cursor.fetchone()

    if not agent or not verify_password(req.password, agent[2], agent[3]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_hex(24)
    now = datetime.utcnow()
    expires_at = now + timedelta(days=7)

    cursor.execute("""
        INSERT INTO agent_sessions (token, agent_id, username, full_name, role, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (token, agent[0], agent[1], agent[4], agent[5], now.isoformat(), expires_at.isoformat()))
    conn.commit()
    conn.close()

    return {
        "token": token,
        "username": agent[1],
        "full_name": agent[4],
        "role": agent[5],
        "expires_at": expires_at.isoformat()
    }

@app.post("/api/auth/logout")
async def api_logout(agent: Optional[dict] = Depends(get_current_agent)):
    if agent and agent.get("token"):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM agent_sessions WHERE token = ?", (agent["token"],))
        conn.commit()
        conn.close()
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def api_me(agent: Optional[dict] = Depends(get_current_agent)):
    if not agent:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return agent

# ==========================================
# Call Logging & Metrics API Endpoints
# ==========================================
@app.post("/api/calls/log")
async def api_log_call(req: CallLogRequest, agent: Optional[dict] = Depends(get_current_agent)):
    agent_name = agent["username"] if agent else "anonymous_agent"
    timestamp = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO call_logs (
            timestamp, agent_username, caller_name, caller_lat, caller_lon,
            dest_name, dest_lat, dest_lon, nearest_station, distance_m,
            duration_min, travel_mode, status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp, agent_name, req.caller_name, req.caller_lat, req.caller_lon,
        req.dest_name, req.dest_lat, req.dest_lon, req.nearest_station, req.distance_m,
        req.duration_min, req.travel_mode, req.status, req.notes
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"status": "success", "log_id": log_id, "timestamp": timestamp}

@app.get("/api/calls/recent")
async def api_recent_calls(limit: int = 15):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, agent_username, caller_name, caller_lat, caller_lon,
               dest_name, nearest_station, distance_m, duration_min, travel_mode, status
        FROM call_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    logs = []
    for r in rows:
        logs.append({
            "id": r[0],
            "timestamp": r[1],
            "agent_username": r[2],
            "caller_name": r[3] or "Caller",
            "caller_lat": r[4],
            "caller_lon": r[5],
            "dest_name": r[6] or "Nearest Taxi",
            "nearest_station": r[7],
            "distance_m": r[8],
            "duration_min": r[9],
            "travel_mode": r[10],
            "status": r[11]
        })
    return {"calls": logs}

@app.get("/api/calls/stats")
async def api_call_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM call_logs")
    total_calls = cursor.fetchone()[0]

    cursor.execute("""
        SELECT nearest_station, COUNT(*) as cnt 
        FROM call_logs 
        GROUP BY nearest_station 
        ORDER BY cnt DESC 
        LIMIT 5
    """)
    top_stations = [{"station": r[0], "count": r[1]} for r in cursor.fetchall()]

    conn.close()
    return {
        "total_calls": total_calls,
        "top_stations": top_stations
    }

# ==========================================
# Navigation & POI Endpoints
# ==========================================
@app.get("/api/places")
async def api_places(category: Optional[str] = None):
    return {"places": get_db_places(category=category)}

@app.post("/api/places")
async def api_create_place(req: PlaceCreateRequest):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Place name cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO places (name, name_am, name_sid, aliases, category, latitude, longitude, description, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        req.name_am.strip() if req.name_am else "",
        req.name_sid.strip() if req.name_sid else "",
        req.aliases.strip() if req.aliases else "",
        req.category.strip() if req.category else "taxi_station",
        req.latitude,
        req.longitude,
        req.description.strip() if req.description else "",
        req.notes.strip() if req.notes else ""
    ))
    place_id = cursor.lastrowid
    cursor.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    # Append to places.csv so it persists across rebuilds
    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                name,
                req.name_am.strip() if req.name_am else "",
                req.name_sid.strip() if req.name_sid else "",
                req.aliases.strip() if req.aliases else "",
                req.category.strip() if req.category else "taxi_station",
                f"{req.latitude:.6f}",
                f"{req.longitude:.6f}",
                req.description.strip() if req.description else "",
                req.notes.strip() if req.notes else ""
            ])
    except Exception:
        pass

    return {
        "status": "success",
        "place": {
            "id": place_id,
            "name": name,
            "name_am": req.name_am,
            "category": req.category or "taxi_station",
            "lat": req.latitude,
            "lon": req.longitude
        }
    }

@app.get("/api/search")
async def api_search(q: str = Query(..., min_length=1)):
    matches = search_db_places(q)
    return {"query": q, "count": len(matches), "results": matches}

@app.get("/api/status")
async def api_status():
    places = get_db_places()
    taxi_count = sum(1 for p in places if p["category"] == "taxi_station")
    landmark_count = len(places) - taxi_count

    valhalla_online = False
    try:
        if http_client:
            res = await http_client.get(f"{VALHALLA_URL}/status")
            valhalla_online = (res.status_code == 200)
    except Exception:
        valhalla_online = False

    ollama_online = False
    try:
        if http_client:
            res = await http_client.get(f"{OLLAMA_URL}/api/tags")
            ollama_online = (res.status_code == 200)
    except Exception:
        ollama_online = False

    return {
        "database": {
            "connected": len(places) > 0,
            "place_count": len(places),
            "taxi_stations": taxi_count,
            "landmarks": landmark_count
        },
        "routing_engine": {
            "type": "Valhalla",
            "online": valhalla_online,
            "url": VALHALLA_URL
        },
        "ai_engine": {
            "type": "Ollama",
            "online": ollama_online,
            "model": "deepseek-r1:1.5b"
        }
    }

@app.post("/api/nearest-taxi")
async def api_nearest_taxi(req: NearestRequest):
    places = get_db_places(category=req.category_filter)
    if not places:
        places = get_db_places(category="taxi_station") or get_db_places()

    if not places:
        raise HTTPException(status_code=404, detail="No places found in database")

    # 1. Pre-filter top 8 candidates by straight-line distance
    candidates = []
    for p in places:
        dist = haversine(req.lat, req.lon, p["lat"], p["lon"])
        candidates.append({
            **p,
            "straight_line_dist_m": round(dist)
        })
    candidates.sort(key=lambda x: x["straight_line_dist_m"])
    top_candidates = candidates[:8]

    # 2. Query Valhalla's road network distance matrix (sources_to_targets) to find the TRUE closest station
    nearest = None
    top_3 = []
    travel_costing = "auto"
    try:
        if http_client:
            matrix_payload = {
                "sources": [{"lat": req.lat, "lon": req.lon}],
                "targets": [{"lat": s["lat"], "lon": s["lon"]} for s in top_candidates],
                "costing": travel_costing
            }
            m_res = await http_client.post(f"{VALHALLA_URL}/sources_to_targets", json=matrix_payload, timeout=4.0)
            if m_res.status_code == 200:
                matrix_data = m_res.json()
                results = matrix_data.get("sources_to_targets", [[]])[0]
                scored = []
                for idx, item in enumerate(results):
                    c = top_candidates[idx]
                    dist_km = item.get("distance")
                    time_s = item.get("time")
                    if dist_km is not None and time_s is not None:
                        road_dist_m = round(dist_km * 1000)
                        scored.append({
                            **c,
                            "distance_m": road_dist_m,
                            "distance_km": round(dist_km, 2),
                            "duration_min": max(1, round(time_s / 60))
                        })
                if scored:
                    # Sort by true shortest road distance and duration
                    scored.sort(key=lambda x: (x["distance_m"], x["duration_min"]))
                    nearest = scored[0]
                    top_3 = scored[:3]
    except Exception:
        pass

    # Fallback to straight-line if matrix was unavailable
    if not nearest:
        nearest = {
            **top_candidates[0],
            "distance_m": top_candidates[0]["straight_line_dist_m"],
            "distance_km": round(top_candidates[0]["straight_line_dist_m"] / 1000, 2),
            "duration_min": max(1, round(top_candidates[0]["straight_line_dist_m"] / 250))
        }
        top_3 = [
            {
                **c,
                "distance_m": c["straight_line_dist_m"],
                "distance_km": round(c["straight_line_dist_m"] / 1000, 2),
                "duration_min": max(1, round(c["straight_line_dist_m"] / 250))
            }
            for c in top_candidates[:3]
        ]

    # 3. Calculate full turn-by-turn route to the TRUE closest station
    walk_route = None
    try:
        valhalla_payload = {
            "locations": [
                {"lat": req.lat, "lon": req.lon},
                {"lat": nearest["lat"], "lon": nearest["lon"]}
            ],
            "costing": travel_costing
        }
        if http_client:
            res = await http_client.post(f"{VALHALLA_URL}/route", json=valhalla_payload, timeout=5.0)
            if res.status_code == 200:
                trip = res.json().get("trip", {})
                leg = trip.get("legs", [{}])[0]
                actual_dist_m = round(trip.get("summary", {}).get("length", 0) * 1000)
                actual_dur_min = max(1, round(trip.get("summary", {}).get("time", 0) / 60))
                walk_route = {
                    "distance_m": actual_dist_m,
                    "duration_min": actual_dur_min,
                    "coordinates": decode_polyline(leg.get("shape", "")),
                    "maneuvers": [m.get("instruction") for m in leg.get("maneuvers", [])]
                }
                # Keep distance and duration synchronized with full route
                nearest["distance_m"] = actual_dist_m
                nearest["distance_km"] = round(actual_dist_m / 1000, 2)
                nearest["duration_min"] = actual_dur_min
    except Exception:
        pass

    return {
        "nearest": nearest,
        "top_stations": top_3,
        "walk_route": walk_route
    }

@app.post("/api/route")
async def api_route(req: RouteRequest):
    costing = req.costing if req.costing in ["pedestrian", "auto", "bicycle"] else "auto"

    valhalla_payload = {
        "locations": [
            {"lat": req.start_lat, "lon": req.start_lon},
            {"lat": req.end_lat, "lon": req.end_lon}
        ],
        "costing": costing
    }

    try:
        if http_client:
            res = await http_client.post(f"{VALHALLA_URL}/route", json=valhalla_payload)
            if res.status_code == 200:
                data = res.json()
                trip = data.get("trip", {})
                leg = trip.get("legs", [{}])[0]
                summary = trip.get("summary", {})

                maneuvers = []
                for m in leg.get("maneuvers", []):
                    dist_m = round(m.get("length", 0) * 1000)
                    maneuvers.append({
                        "instruction": m.get("instruction", "Proceed"),
                        "distance_m": dist_m
                    })

                return {
                    "engine": "valhalla",
                    "distance_m": round(summary.get("length", 0) * 1000),
                    "duration_min": max(1, round(summary.get("time", 0) / 60)),
                    "coordinates": decode_polyline(leg.get("shape", "")),
                    "maneuvers": maneuvers
                }
    except Exception:
        pass

    # Fallback: direct line haversine
    dist_direct = round(haversine(req.start_lat, req.start_lon, req.end_lat, req.end_lon))
    duration_estimate = round(dist_direct / (1.2 if costing == "pedestrian" else 8.3) / 60)
    return {
        "engine": "fallback_haversine",
        "distance_m": dist_direct,
        "duration_min": max(1, duration_estimate),
        "coordinates": [
            [req.start_lat, req.start_lon],
            [req.end_lat, req.end_lon]
        ],
        "maneuvers": [
            {"instruction": f"Head directly towards destination ({dist_direct} m straight-line)", "distance_m": dist_direct}
        ]
    }

# ==========================================
# Phase 3: Offline AI Dispatch Assistant
# ==========================================
@app.post("/api/ai/dispatch")
async def api_ai_dispatch(req: AIDispatchRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text inquiry")

    places = get_db_places()
    found_origin = None
    found_dest = None

    # Step 1: Fast direct FTS / keyword matching against all known Hawassa places
    matched_places = []
    for p in places:
        # Check primary name, Amharic name, or aliases
        keywords = [p["name"].lower()]
        if p["name_am"]:
            keywords.append(p["name_am"].lower())
        if p["aliases"]:
            keywords.extend([a.strip().lower() for a in p["aliases"].split(",")])

        for kw in keywords:
            if kw and kw in text.lower():
                matched_places.append(p)
                break

    if len(matched_places) >= 2:
        found_origin = matched_places[0]
        found_dest = matched_places[1]
    elif len(matched_places) == 1:
        found_origin = matched_places[0]

    # Step 2: If locations not fully resolved, invoke local Ollama LLM to parse text
    if not found_origin or ((" to " in text.lower() or " ወደ " in text or "destination" in text.lower()) and not found_dest):
        try:
            prompt = f"""Extract caller origin and destination in Hawassa, Ethiopia.
Caller query: "{text}"
Respond ONLY in valid JSON:
{{"origin": "origin place name", "destination": "destination place name or null"}}"""
            if http_client:
                ollama_res = await http_client.post(f"{OLLAMA_URL}/api/generate", json={
                    "model": "deepseek-r1:1.5b",
                    "prompt": prompt,
                    "stream": False
                }, timeout=6.0)
                if ollama_res.status_code == 200:
                    raw_resp = ollama_res.json().get("response", "")
                    json_match = re.search(r'\{.*\}', raw_resp, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        orig_text = parsed.get("origin")
                        dest_text = parsed.get("destination")
                        if orig_text and not found_origin:
                            matches = search_db_places(orig_text)
                            if matches:
                                found_origin = matches[0]
                        if dest_text and not found_dest:
                            matches = search_db_places(dest_text)
                            if matches:
                                found_dest = matches[0]
        except Exception:
            pass

    # If still no origin found, fallback to central Hawassa
    if not found_origin:
        found_origin = places[0] if places else {"name": "Hawassa Center", "lat": 7.0504, "lon": 38.4763}

    # Calculate nearest taxi station from origin
    nearest_res = await api_nearest_taxi(NearestRequest(lat=found_origin["lat"], lon=found_origin["lon"]))
    nearest_station = nearest_res["nearest"]

    # Calculate route if destination found
    route_data = None
    if found_dest:
        route_data = await api_route(RouteRequest(
            start_lat=found_origin["lat"],
            start_lon=found_origin["lon"],
            end_lat=found_dest["lat"],
            end_lon=found_dest["lon"],
            costing="auto"
        ))

    # Dual-language agent talk-track scripts
    station_name = nearest_station["name"]
    station_am = nearest_station.get("name_am") or station_name
    dist_m = nearest_station["distance_m"]

    if route_data and found_dest:
        dest_name = found_dest["name"]
        dest_am = found_dest.get("name_am") or dest_name
        total_km = round(route_data["distance_m"] / 1000, 2)
        duration_m = route_data["duration_min"]

        script_en = f"Your closest taxi/bajaj point is {station_name} ({dist_m}m walk). The route to {dest_name} is {total_km} km (about {duration_m} minutes)."
        script_am = f"ለእርስዎ የቀረበው ባጃጅ/ታክሲ ማቆሚያ {station_am} ነው ({dist_m} ሜትር)። ወደ {dest_am} ያለው ርቀት {total_km} ኪ.ሜ (በግምት {duration_m} ደቂቃ) ነው።"
    else:
        script_en = f"The closest taxi terminal from your position is {station_name}, approximately {dist_m} meters away."
        script_am = f"ከእርስዎ አካባቢ በጣም የቀረበው የታክሲ ማቆሚያ {station_am} ነው ({dist_m} ሜትር ርቀት)።"

    return {
        "status": "success",
        "inquiry": text,
        "origin": found_origin,
        "destination": found_dest,
        "nearest_station": nearest_station,
        "route": route_data,
        "script_en": script_en,
        "script_am": script_am
    }

INDEX_PATH = os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/", response_class=HTMLResponse)
async def index_page():
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Hawassa Navigation System</h1><p>Index template missing.</p>"

if os.path.exists(os.path.join(os.path.dirname(__file__), "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8080, reload=False)
