import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")

def search_place(query):
    if not os.path.exists(DB_PATH):
        return f"Database not found at {DB_PATH}. Please run import_places.py first."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Try FTS5 first
    results = []
    try:
        cursor.execute("""
            SELECT p.name, p.name_am, p.category, p.latitude, p.longitude, p.description
            FROM places_fts f
            JOIN places p ON f.rowid = p.id
            WHERE places_fts MATCH ?
            LIMIT 10
        """, (f'"{query.strip()}"*',))
        results = cursor.fetchall()
    except Exception:
        pass

    if not results:
        like_term = f"%{query.strip()}%"
        cursor.execute("""
            SELECT name, name_am, category, latitude, longitude, description
            FROM places
            WHERE name LIKE ? OR name_am LIKE ? OR name_sid LIKE ? OR aliases LIKE ?
            ORDER BY name
            LIMIT 10
        """, (like_term, like_term, like_term, like_term))
        results = cursor.fetchall()
    
    conn.close()
    
    if not results:
        return f"No matching places found for '{query}'."
    
    output = []
    for place in results:
        am_tag = f" ({place[1]})" if place[1] else ""
        cat_icon = "🚖" if place[2] == "taxi_station" else "🏛️"
        output.append(f"{cat_icon} {place[0]}{am_tag}")
        output.append(f"   Category: {place[2]}")
        output.append(f"   Coordinates: {place[3]}, {place[4]}")
        if place[5]:
            output.append(f"   Info: {place[5]}")
        output.append("")
    
    return "\n".join(output)


if __name__ == "__main__":
    test_queries = sys.argv[1:] if len(sys.argv) > 1 else ["መናኸሪያ", "piazza", "referral", "ሀይሌ"]
    for q in test_queries:
        print(f"=== Search: '{q}' ===")
        print(search_place(q))
