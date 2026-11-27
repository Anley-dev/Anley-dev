import sqlite3
import math
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points in meters using the Haversine formula.
    """
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_taxi(current_lat, current_lon, top_n=3):
    """
    Find the nearest taxi stations from a given location.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}. Please run import_places.py first.")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name, latitude, longitude, description FROM places")
    places = cursor.fetchall()
    conn.close()

    distances = []
    for name, lat, lon, description in places:
        distance = haversine(current_lat, current_lon, lat, lon)
        distances.append({
            "name": name,
            "latitude": lat,
            "longitude": lon,
            "description": description,
            "distance_meters": round(distance),
            "distance_km": round(distance / 1000, 2)
        })

    # Sort by nearest
    distances.sort(key=lambda x: x["distance_meters"])

    return distances[:top_n]


if __name__ == "__main__":
    # Example: Caller is near the city center (7.0300, 38.4800)
    caller_lat = 7.0300
    caller_lon = 38.4800

    nearest = find_nearest_taxi(caller_lat, caller_lon, top_n=3)

    print(f"Nearest Taxi Stations to ({caller_lat}, {caller_lon}):\n")
    for i, station in enumerate(nearest, 1):
        print(f"{i}. {station['name']}")
        print(f"   Distance: {station['distance_meters']} meters ({station['distance_km']} km)")
        print(f"   Coordinates: {station['latitude']}, {station['longitude']}")
        if station['description']:
            print(f"   Info: {station['description']}")
        print()
