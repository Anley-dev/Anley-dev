import sqlite3
import math
import os
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

# ======================
# Database helpers
# ======================
def get_all_places():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, name_am, aliases, latitude, longitude, description, category FROM places")
    places = cursor.fetchall()
    conn.close()
    return places


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def search_place_by_name(query):
    places = get_all_places()
    query = query.lower().strip()
    if not query:
        return []
    matches = []

    for name, name_am, aliases, lat, lon, desc, category in places:
        match_str = f"{name} {name_am or ''} {aliases or ''}".lower()
        if query in match_str:
            display_name = f"{name} ({name_am})" if name_am else name
            matches.append({
                "name": display_name,
                "lat": lat,
                "lon": lon,
                "description": desc,
                "category": category
            })
    return matches


def find_nearest_taxi(lat, lon):
    places = get_all_places()
    nearest = None
    min_dist = float("inf")

    for name, name_am, aliases, plat, plon, desc, category in places:
        # Prioritize taxi stations
        dist = haversine(lat, lon, plat, plon)
        if dist < min_dist:
            min_dist = dist
            display_name = f"{name} ({name_am})" if name_am else name
            nearest = {
                "name": display_name,
                "lat": plat,
                "lon": plon,
                "description": desc,
                "distance_m": round(dist)
            }
    return nearest
    return nearest


# ======================
# OSRM directions
# ======================
def get_route(start_lon, start_lat, end_lon, end_lat, profile="walking", osrm_url="http://localhost:5000"):
    url = f"{osrm_url}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
    params = {"steps": "true", "overview": "false"}

    try:
        res = requests.get(url, params=params, timeout=4)
        data = res.json()
        if data.get("code") != "Ok":
            return None

        route = data["routes"][0]
        steps = []
        for i, step in enumerate(route["legs"][0]["steps"], 1):
            instruction = step["maneuver"].get("instruction", "Proceed")
            dist = round(step["distance"])
            steps.append(f"{i}. {instruction} ({dist} m)")

        return {
            "distance": round(route["distance"]),
            "duration": max(1, round(route["duration"] / 60)),
            "steps": steps
        }
    except:
        return None


# ======================
# Get coordinates (name or lat,lon)
# ======================
def get_location(prompt):
    while True:
        value = input(prompt).strip()
        if not value:
            continue

        # Try coordinates first if comma is present
        if "," in value:
            try:
                lat, lon = map(float, value.split(","))
                return lat, lon
            except ValueError:
                pass

        # Try name search
        matches = search_place_by_name(value)
        if matches:
            if len(matches) == 1:
                place = matches[0]
                print(f"  → Found: {place['name']} ({place['lat']}, {place['lon']})")
                return place["lat"], place["lon"]
            else:
                print(f"\nMultiple matches found for '{value}':")
                for i, p in enumerate(matches, 1):
                    print(f"  {i}. {p['name']}")
                choice = input("Choose number: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(matches):
                        place = matches[idx]
                        print(f"  → Selected: {place['name']} ({place['lat']}, {place['lon']})")
                        return place["lat"], place["lon"]
                except:
                    print("Invalid choice, please re-enter.")
                    continue

        print("❌ Could not understand. Type a place name (e.g., 'central', 'lake', 'aisha') or coordinates ('7.03, 38.48')")


# ======================
# Main Interface
# ======================
def main():
    print("=" * 55)
    print("     Hawassa Call Center Navigation System (v2)")
    print("=" * 55)

    while True:
        print("\nOptions:")
        print("1. Full directions (Current location → Destination)")
        print("2. Only find nearest taxi station")
        print("3. Exit")

        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "3":
            print("Goodbye!")
            break

        try:
            print("\n--- Caller's Current Location ---")
            print("Type a place name (e.g. 'central', 'university', 'aisha') or coordinates (e.g. 7.03, 38.48):")
            current_lat, current_lon = get_location("Current location: ")

            if choice == "1":
                print("\n--- Destination ---")
                dest_lat, dest_lon = get_location("Destination: ")

                profile = input("\nProfile (walking / driving) [walking]: ").strip().lower()
                if profile not in ["walking", "driving"]:
                    profile = "walking"

                print("\n" + "=" * 55)
                print("RESULT FOR AGENT")
                print("=" * 55)

                # Nearest taxi
                nearest = find_nearest_taxi(current_lat, current_lon)
                if nearest:
                    print(f"\n📍 Nearest Taxi Station from caller:")
                    print(f"   → {nearest['name']} ({nearest['distance_m']} meters away)")
                    if nearest['description']:
                        print(f"   → Info: {nearest['description']}")

                # Full route
                route = get_route(current_lon, current_lat, dest_lon, dest_lat, profile)
                if route:
                    print(f"\n🗺️  Directions to destination ({profile}):")
                    print(f"   Distance : {route['distance']} meters")
                    print(f"   Time     : about {route['duration']} minutes\n")
                    print("Turn-by-turn:")
                    for step in route["steps"]:
                        print("  " + step)
                else:
                    dist_direct = round(haversine(current_lat, current_lon, dest_lat, dest_lon))
                    print(f"\n⚠️  Road route calculation unavailable (OSRM server offline).")
                    print(f"   Direct straight-line distance: {dist_direct} meters ({round(dist_direct/1000, 2)} km)")

            elif choice == "2":
                nearest = find_nearest_taxi(current_lat, current_lon)
                if nearest:
                    print("\n📍 Nearest Taxi Station:")
                    print(f"   Name     : {nearest['name']}")
                    print(f"   Distance : {nearest['distance_m']} meters")
                    print(f"   Location : {nearest['lat']}, {nearest['lon']}")
                    if nearest['description']:
                        print(f"   Info     : {nearest['description']}")
                else:
                    print("No taxi station found.")

        except Exception as e:
            print(f"\n❌ Error: {e}")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
