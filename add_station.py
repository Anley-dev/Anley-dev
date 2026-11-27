#!/usr/bin/env python3
"""
Hawassa Call Center — Add New Taxi / Bajaj Station Tool
Usage:
    python3 add_station.py
    python3 add_station.py --name "Station Name" --name-am "የጣቢያ ስም" --lat 7.0512 --lon 38.4789
"""

import sys
import os
import sqlite3
import csv
import argparse

DB_PATH = os.path.join(os.path.dirname(__file__), "hawassa_places.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "places.csv")

def add_station(name, name_am="", name_sid="", aliases="", category="taxi_station", lat=0.0, lon=0.0, description="", notes=""):
    if not name or not lat or not lon:
        print("❌ Error: Name, Latitude, and Longitude are required.")
        return False

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO places (name, name_am, name_sid, aliases, category, latitude, longitude, description, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name.strip(), name_am.strip(), name_sid.strip(), aliases.strip(), category.strip(), float(lat), float(lon), description.strip(), notes.strip()))

    new_id = cur.lastrowid
    cur.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()

    # Append to places.csv
    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([name.strip(), name_am.strip(), name_sid.strip(), aliases.strip(), category.strip(), f"{float(lat):.6f}", f"{float(lon):.6f}", description.strip(), notes.strip()])
    except Exception as e:
        print(f"⚠️ Warning: Could not append to places.csv: {e}")

    print("\n" + "=" * 50)
    print(f"✅ Successfully added new station (ID: {new_id})")
    print(f"   Name (EN):    {name}")
    print(f"   Name (AM):    {name_am or 'N/A'}")
    print(f"   Coordinates:  {float(lat):.6f}, {float(lon):.6f}")
    print(f"   Category:     {category}")
    print(f"   Description:  {description or 'N/A'}")
    print("=" * 50 + "\n")
    return True

def interactive_mode():
    print("\n🚖 --- Hawassa Navigation: Add New Taxi / Bajaj Station ---")
    print("Fill in the station details below:\n")

    name = input("1. Station Name in English (e.g. Millennium North Stand): ").strip()
    if not name:
        print("Name cannot be empty. Exiting.")
        return

    name_am = input("2. Station Name in Amharic (e.g. ሚሊኒየም ሰሜን ማቆሚያ) [Optional]: ").strip()
    
    lat_str = input("3. Latitude (e.g. 7.054321): ").strip()
    lon_str = input("4. Longitude (e.g. 38.481234): ").strip()

    try:
        lat = float(lat_str)
        lon = float(lon_str)
    except ValueError:
        print("❌ Invalid coordinates. Latitude and Longitude must be numbers.")
        return

    aliases = input("5. Aliases / Search Keywords (comma-separated, e.g. millenium, 05 gate) [Optional]: ").strip()
    description = input("6. Description (e.g. Bajaj stand near school gate) [Optional]: ").strip()

    add_station(name=name, name_am=name_am, aliases=aliases, lat=lat, lon=lon, description=description)

def main():
    parser = argparse.ArgumentParser(description="Add a new taxi station to Hawassa places database")
    parser.add_argument("--name", help="English name of the taxi station")
    parser.add_argument("--name-am", default="", help="Amharic name")
    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lon", type=float, help="Longitude")
    parser.add_argument("--aliases", default="", help="Search keywords comma-separated")
    parser.add_argument("--desc", default="", help="Description")

    args = parser.parse_args()

    if args.name and args.lat and args.lon:
        add_station(name=args.name, name_am=args.name_am, aliases=args.aliases, lat=args.lat, lon=args.lon, description=args.desc)
    else:
        interactive_mode()

if __name__ == "__main__":
    main()
