# Hawassa Call Center Navigation System — Agent Quick Guide

Welcome to the Hawassa Call Center Navigation Tool! This guide explains how to look up taxi terminals, find the nearest pickup points for callers, and provide turn-by-turn routing across Hawassa.

---

## 1. Quick Start

Ensure your database is initialized:
```bash
python3 import_places.py
```

Launch the interactive assistant:
```bash
python3 agent_interface_v2.py
```

---

## 2. Main Menu Options

When the script runs, you will see 3 options:
```text
Options:
1. Full directions (Current location → Destination)
2. Only find nearest taxi station
3. Exit
```

### Option 1: Full directions
Use this when a caller asks: *"I am at [Location A] and need to get to [Location B]. Where is the nearest taxi and how do I get there?"*

1. **Enter Caller's Current Location**:
   - You can type the landmark / place name (e.g. `central`, `university`, `aisha`, `lake`).
   - Or enter GPS coordinates (e.g. `7.0300, 38.4800`).
2. **Enter Destination**:
   - Type destination name or GPS coordinates.
3. **Select Mode**:
   - Press `Enter` for walking (default) or type `driving`.
4. **Agent Response to Caller**:
   - Give the caller their nearest taxi point and distance in meters.
   - Read the step-by-step turn directions or total trip distance/time.

### Option 2: Nearest taxi station only
Use this when a caller simply asks: *"Where can I catch a taxi/bajaj from where I am right now?"*
- Enter caller's current place name or coordinates.
- System instantly outputs the closest station name, distance, and coordinates.

---

## 3. Recognized Taxi Points in Hawassa

| Point Name | Key Aliases / Search Keywords | Area / Vicinity |
|---|---|---|
| **Taxi - South** | `south taxi`, `southern taxi` | Southern Hawassa |
| **Taxi - Near Aisha Mosque** | `aisha`, `aisha mosque` | Near Aisha Mosque |
| **Taxi - Central** | `central`, `city center`, `main taxi` | City Center |
| **Taxi - West Central** | `west central` | West of City Center |
| **Taxi - Mid Area** | `mid area`, `middle` | Mid area |
| **Taxi - Lake Side** | `lake`, `lake side` | Near Lake Hawassa |
| **Taxi - North Central** | `north central` | North of Center |
| **Taxi - East Central** | `east central` | East of Center |
| **Taxi - University Area** | `university`, `hu taxi`, `hu` | Hawassa University Area |
| **Taxi - North East** | `north east` | North-East area |
| **Taxi - Far North** | `far north`, `northern` | Northern part |
| **Taxi - East Side** | `east side`, `eastern` | Eastern side |

---

## 4. Script Reference & Utilities

| Script | Purpose | Command |
|---|---|---|
| [agent_interface_v2.py](file:///home/anley/dogo/agent_interface_v2.py) | **Primary interactive agent console** (supports names & coordinates) | `python3 agent_interface_v2.py` |
| [search_places.py](file:///home/anley/dogo/search_places.py) | Quick name & alias search | `python3 search_places.py` |
| [nearest_taxi.py](file:///home/anley/dogo/nearest_taxi.py) | Fast offline nearest-point calculation | `python3 nearest_taxi.py` |
| [combined_nearest_taxi.py](file:///home/anley/dogo/combined_nearest_taxi.py) | Nearest taxi + OSRM directions | `python3 combined_nearest_taxi.py` |
| [full_navigation.py](file:///home/anley/dogo/full_navigation.py) | Caller location → nearest taxi + destination routing | `python3 full_navigation.py` |
| [import_places.py](file:///home/anley/dogo/import_places.py) | Populates `hawassa_places.db` from `places.csv` | `python3 import_places.py` |

---

## 5. Troubleshooting & Tips

- **Multiple Name Matches**: If you type `east`, the system will ask you to select between *Taxi - East Central* and *Taxi - East Side*. Just enter `1` or `2`.
- **OSRM Router Offline**: If the local OSRM routing server on port `5000` is offline, the tools automatically fall back to providing accurate straight-line (Haversine) distances and nearest taxi identification without crashing.
