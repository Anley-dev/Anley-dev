import os
import json
import sqlite3
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "hawassa_places.db")
GEOJSON_PATH = "/tmp/hawassa_pois.geojson"
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "places.csv")

CATEGORY_MAP = {
    "hotel": "hotel",
    "motel": "hotel",
    "guest_house": "hotel",
    "apartment": "hotel",
    "bank": "bank",
    "atm": "bank",
    "fuel": "fuel",
    "hospital": "hospital",
    "clinic": "hospital",
    "dentist": "hospital",
    "school": "school",
    "college": "school",
    "university": "school",
    "library": "school",
    "restaurant": "restaurant",
    "cafe": "restaurant",
    "bar": "restaurant",
    "fast_food": "restaurant",
    "pub": "restaurant",
    "place_of_worship": "worship",
    "marketplace": "market",
    "supermarket": "market",
    "kiosk": "market",
    "taxi": "taxi_station",
    "bus_station": "taxi_station"
}

def run_import():
    if not os.path.exists(GEOJSON_PATH):
        print(f"Error: {GEOJSON_PATH} does not exist.")
        return

    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing names to avoid duplicates
    cursor.execute("SELECT LOWER(name) FROM places")
    existing_names = set(r[0] for r in cursor.fetchall())

    new_places = []
    for ft in data.get("features", []):
        props = ft.get("properties", {})
        geom = ft.get("geometry", {})
        name = props.get("name")
        if not name or len(name.strip()) < 2:
            continue

        name = name.strip()
        if name.lower() in existing_names:
            continue

        raw_cat = props.get("amenity") or props.get("tourism") or props.get("shop") or "landmark"
        cat = CATEGORY_MAP.get(raw_cat, "landmark")

        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue

        lon = float(coords[0])
        lat = float(coords[1])

        # Validate within Hawassa bounds
        if not (38.40 <= lon <= 38.56 and 6.98 <= lat <= 7.14):
            continue

        name_am = props.get("name:am", "")
        aliases = f"{name.lower()}, {raw_cat}"

        desc = f"{cat.replace('_', ' ').capitalize()} in Hawassa"
        if raw_cat in ["bank", "hotel", "fuel", "hospital", "restaurant"]:
            desc = f"Local {raw_cat.capitalize()} ({name})"

        new_places.append((name, name_am, "", aliases, cat, lat, lon, desc, f"OSM {raw_cat}"))
        existing_names.add(name.lower())

    print(f"Adding {len(new_places)} new named places, hotels, banks, and POIs...")

    for p in new_places:
        cursor.execute("""
            INSERT INTO places (name, name_am, name_sid, aliases, category, latitude, longitude, description, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, p)
        place_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO places_fts (rowid, name, name_am, name_sid, aliases, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (place_id, p[0], p[1], p[2], p[3], p[7]))

    conn.commit()

    cursor.execute("SELECT COUNT(*), category FROM places GROUP BY category")
    counts = cursor.fetchall()
    print("\nUpdated Places Database Summary:")
    for cnt, c in counts:
        print(f"  - {c}: {cnt}")

    cursor.execute("SELECT COUNT(*) FROM places")
    total = cursor.fetchone()[0]
    print(f"\n✅ Total Places now in Database: {total}")

    conn.close()

if __name__ == "__main__":
    run_import()
