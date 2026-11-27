import sqlite3
import math
import os
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

# ======================
# Helper: Calculate distance
# ======================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ======================
# Find nearest taxi
# ======================
def find_nearest_taxi(lat, lon):
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, latitude, longitude, description FROM places")
    places = cursor.fetchall()
    conn.close()

    nearest = None
    min_distance = float("inf")

    for name, plat, plon, desc in places:
        dist = haversine(lat, lon, plat, plon)
        if dist < min_distance:
            min_distance = dist
            nearest = {
                "name": name,
                "lat": plat,
                "lon": plon,
                "description": desc,
                "distance_m": round(dist),
                "distance_km": round(dist / 1000, 2)
            }
    return nearest


# ======================
# Get directions from OSRM
# ======================
def get_route(start_lon, start_lat, end_lon, end_lat, profile="walking", osrm_url="http://localhost:5000"):
    url = f"{osrm_url}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {
        "steps": "true",
        "overview": "false"
    }

    try:
        res = requests.get(url, params=params, timeout=4)
        data = res.json()

        if data.get("code") != "Ok":
            return None

        route = data["routes"][0]
        legs = route["legs"][0]

        steps = []
        for i, step in enumerate(legs["steps"], 1):
            instruction = step["maneuver"].get("instruction", "Proceed")
            distance = round(step["distance"])
            steps.append(f"{i}. {instruction} ({distance} m)")

        return {
            "distance_m": round(route["distance"]),
            "duration_min": max(1, round(route["duration"] / 60)),
            "steps": steps
        }
    except requests.exceptions.ConnectionError:
        return {"error": f"OSRM router at {osrm_url} is not running."}
    except Exception as e:
        return {"error": str(e)}


# ======================
# Main function for call center
# ======================
def handle_call(current_lat, current_lon, dest_lat, dest_lon, profile="walking"):
    result = []

    # 1. Nearest taxi from caller
    nearest = find_nearest_taxi(current_lat, current_lon)
    if nearest:
        result.append("📍 Nearest Taxi Station from caller:")
        result.append(f"   → {nearest['name']}")
        result.append(f"   → {nearest['distance_m']} meters away ({nearest['distance_km']} km)")
        if nearest['description']:
            result.append(f"   → Info: {nearest['description']}")
        result.append("")

    # Direct straight-line distance
    direct_dist = round(haversine(current_lat, current_lon, dest_lat, dest_lon))
    result.append(f"📏 Direct Distance to Destination: {direct_dist} meters ({round(direct_dist/1000, 2)} km)")

    # 2. Full route from current location to destination
    route = get_route(current_lon, current_lat, dest_lon, dest_lat, profile=profile)

    if not route or "error" in route:
        err_msg = route.get("error") if route else "Could not calculate route."
        result.append(f"⚠️ Road route unavailable ({err_msg})")
        return "\n".join(result)

    result.append(f"\n🗺️ Route to Destination ({profile}):")
    result.append(f"   Road Distance: {route['distance_m']} meters")
    result.append(f"   Estimated time: {route['duration_min']} minutes")
    result.append("")
    result.append("Directions:")
    result.extend(route["steps"])

    return "\n".join(result)


# ======================
# Example usage
# ======================
if __name__ == "__main__":
    current_lat = 7.0300
    current_lon = 38.4800

    dest_lat = 7.0500
    dest_lon = 38.4900

    print("===== WALKING =====")
    print(handle_call(current_lat, current_lon, dest_lat, dest_lon, profile="walking"))

    print("\n\n===== DRIVING =====")
    print(handle_call(current_lat, current_lon, dest_lat, dest_lon, profile="driving"))
