import sqlite3
import math
import os
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

# ======================
# Distance calculation
# ======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ======================
# Find nearest taxi stations
# ======================
def find_nearest_taxis(current_lat, current_lon, top_n=3):
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, latitude, longitude, description FROM places")
    places = cursor.fetchall()
    conn.close()

    results = []
    for name, lat, lon, description in places:
        distance = haversine(current_lat, current_lon, lat, lon)
        results.append({
            "name": name,
            "lat": lat,
            "lon": lon,
            "description": description,
            "distance_m": round(distance),
            "distance_km": round(distance / 1000, 2)
        })

    results.sort(key=lambda x: x["distance_m"])
    return results[:top_n]


# ======================
# Get directions from OSRM
# ======================
def get_directions(start_lon, start_lat, end_lon, end_lat, profile="walking", osrm_url="http://localhost:5000"):
    url = f"{osrm_url}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {
        "steps": "true",
        "overview": "false",
        "geometries": "geojson"
    }

    try:
        response = requests.get(url, params=params, timeout=4)
        data = response.json()

        if data.get("code") != "Ok":
            return "Could not calculate route via OSRM."

        route = data["routes"][0]
        legs = route["legs"][0]

        directions = []
        directions.append(f"Distance: {round(route['distance'])} meters")
        directions.append(f"Time: about {max(1, round(route['duration'] / 60))} minutes")
        directions.append("")
        directions.append("Directions:")

        for i, step in enumerate(legs["steps"], 1):
            instruction = step["maneuver"].get("instruction", "Proceed")
            dist = round(step["distance"])
            directions.append(f"{i}. {instruction} ({dist} m)")

        return "\n".join(directions)

    except requests.exceptions.ConnectionError:
        return f"[Notice: OSRM router at {osrm_url} is currently offline. Direct straight-line distance is available above.]"
    except Exception as e:
        return f"Error getting directions: {str(e)}"


# ======================
# Main function
# ======================
def get_nearest_taxi_with_directions(current_lat, current_lon, profile="walking"):
    nearest = find_nearest_taxis(current_lat, current_lon, top_n=1)

    if not nearest:
        return "No taxi stations found in the database. Please ensure import_places.py was run."

    station = nearest[0]

    result = []
    result.append(f"Nearest Taxi Station: {station['name']}")
    result.append(f"Distance: {station['distance_m']} meters ({station['distance_km']} km)")
    if station['description']:
        result.append(f"Info: {station['description']}")
    result.append("")
    result.append("——— Directions ———")
    result.append(get_directions(
        current_lon, current_lat,
        station['lon'], station['lat'],
        profile=profile
    ))

    return "\n".join(result)


# ======================
# Example usage
# ======================
if __name__ == "__main__":
    caller_lat = 7.0300
    caller_lon = 38.4800

    print("=== Walking directions ===")
    print(get_nearest_taxi_with_directions(caller_lat, caller_lon, profile="walking"))

    print("\n\n=== Driving directions ===")
    print(get_nearest_taxi_with_directions(caller_lat, caller_lon, profile="driving"))
