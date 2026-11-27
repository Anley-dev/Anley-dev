import sqlite3
import csv
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "places.csv")

def import_places():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS places")
    cursor.execute("DROP TABLE IF EXISTS places_fts")

    cursor.execute("""
    CREATE TABLE places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        name_am TEXT,
        name_sid TEXT,
        aliases TEXT,
        category TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        description TEXT,
        notes TEXT
    )
    """)

    # FTS5 full-text search table for instant multilingual indexing
    cursor.execute("""
    CREATE VIRTUAL TABLE places_fts USING fts5(
        name,
        name_am,
        name_sid,
        aliases,
        description,
        content=places,
        content_rowid=id
    )
    """)

    count = 0
    with open(CSV_PATH, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute("""
                INSERT INTO places (name, name_am, name_sid, aliases, category, latitude, longitude, description, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row["name"].strip(),
                row.get("name_am", "").strip(),
                row.get("name_sid", "").strip(),
                row.get("aliases", "").strip(),
                row.get("category", "taxi_station").strip(),
                float(row["latitude"]),
                float(row["longitude"]),
                row.get("description", "").strip(),
                row.get("notes", "").strip()
            ))
            place_id = cursor.lastrowid

            # Sync with FTS table
            cursor.execute("""
                INSERT INTO places_fts (rowid, name, name_am, name_sid, aliases, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                place_id,
                row["name"].strip(),
                row.get("name_am", "").strip(),
                row.get("name_sid", "").strip(),
                row.get("aliases", "").strip(),
                row.get("description", "").strip()
            ))
            count += 1

    conn.commit()
    conn.close()
    print(f"✅ Successfully imported {count} multilingual places and POIs into {DB_PATH}")

if __name__ == "__main__":
    import_places()
