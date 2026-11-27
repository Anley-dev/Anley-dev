import sqlite3
import math
import os
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

# ======================
# Helper functions
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


def find_nearest_taxi(lat, lon):
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, latitude, longitude, description FROM places")
    places = cursor.fetchall()
    conn.close()

    nearest = None
    min_dist = float("inf")

    for name, plat, plon, desc in places:
        dist = haversine(lat, lon, plat, plon)
        if dist < min_dist:
            min_dist = dist
            nearest = {
                "name": name,
                "lat": plat,
                "lon": plon,
                "description": desc,
                "distance_m": round(dist)
            }
    return nearest


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
# Main Interface
# ======================
def main():
    print("=" * 50)
    print("   Hawassa Call Center Navigation System")
    print("=" * 50)

    while True:
        print("\nOptions:")
        print("1. Find nearest taxi + directions to destination")
        print("2. Only find nearest taxi station")
        print("3. Exit")

        choice = input("\nEnter choice (1/2/3): ").strip()

        if choice == "3":
            print("Goodbye!")
            break

        try:
            print("\nEnter Caller's Current Location:")
            current_lat = float(input("Latitude  : "))
            current_lon = float(input("Longitude : "))

            if choice == "1":
                print("\nEnter Destination:")
                dest_lat = float(input("Latitude  : "))
                dest_lon = float(input("Longitude : "))

                profile = input("\nProfile (walking / driving) [walking]: ").strip().lower()
                if profile not in ["walking", "driving"]:
                    profile = "walking"

                print("\n" + "=" * 50)
                print("RESULT")
                print("=" * 50)

                # Nearest taxi
                nearest = find_nearest_taxi(current_lat, current_lon)
                if nearest:
                    print(f"\n📍 Nearest Taxi Station:")
                    print(f"   {nearest['name']}")
                    print(f"   Distance: {nearest['distance_m']} meters")
                    if nearest['description']:
                        print(f"   Info: {nearest['description']}")

                # Full route
                route = get_route(current_lon, current_lat, dest_lon, dest_lat, profile)
                if route:
                    print(f"\n🗺️  Route to Destination ({profile}):")
                    print(f"   Distance : {route['distance']} meters")
                    print(f"   Time     : ~{route['duration']} minutes\n")
                    print("Directions:")
                    for step in route["steps"]:
                        print("  " + step)
                else:
                    dist_direct = round(haversine(current_lat, current_lon, dest_lat, dest_lon))
                    print(f"\n⚠️  Road routing unavailable. Direct distance: {dist_direct} m")

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
                    print("No taxi stations found.")

        except ValueError:
            print("\n❌ Invalid input. Please enter numbers only.")
        except Exception as e:
            print(f"\n❌ Error: {e}")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
