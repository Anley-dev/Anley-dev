-- Enable foreign key support
PRAGMA foreign_keys = ON;

-- Core Places & Landmarks (Hawassa POIs)
CREATE TABLE places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                -- English name (e.g., "Hawassa University")
    name_am TEXT,                      -- Amharic name (e.g., "ሐዋሳ ዩኒቨርሲቲ")
    name_sid TEXT,                     -- Sidaamu Afoo name
    type TEXT NOT NULL,                -- university, hospital, landmark, kebele, market
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    kebele TEXT                        -- e.g., "05", "Menharya"
);

-- Multilingual Aliases for Fuzzy Search (handles transliterations)
CREATE TABLE aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id INTEGER NOT NULL,
    alias TEXT NOT NULL,               -- e.g., "Menharya", "Minariya", "መናኸሪያ"
    language TEXT NOT NULL,            -- 'en', 'am', 'sid'
    FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
);

-- SQLite FTS5 Virtual Table for Fast, Offline Full-Text Search
-- Includes place names and aggregate aliases
CREATE VIRTUAL TABLE places_fts USING fts5(
    name, 
    name_am, 
    name_sid, 
    aliases
);

-- Local Roads & Valhalla Linkage
CREATE TABLE roads (
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,                         -- trunk, primary, residential, unpaved
    surface TEXT,                      -- asphalt, gravel, dirt
    oneway INTEGER DEFAULT 0,
    maxspeed INTEGER,
    geometry TEXT                      -- Encoded polyline or JSON coordinates
);

-- Taxi & Bajaj Terminals (Hawassa Public Transport Intelligence)
CREATE TABLE taxi_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                -- e.g., "Menharya Taxi Terminal"
    destination TEXT NOT NULL,         -- e.g., "05", "Piazza"
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    avg_fare_etb REAL                  -- Estimated typical fare
);

-- Indexes for rapid local lookup
CREATE INDEX idx_places_coords ON places(latitude, longitude);
CREATE INDEX idx_aliases_text ON aliases(alias);
CREATE INDEX idx_taxi_dest ON taxi_stations(destination);

-- Triggers to keep FTS index synchronized automatically
CREATE TRIGGER places_ai AFTER INSERT ON places BEGIN
    INSERT INTO places_fts(rowid, name, name_am, name_sid, aliases)
    VALUES (new.id, new.name, new.name_am, new.name_sid, '');
END;

CREATE TRIGGER places_ad AFTER DELETE ON places BEGIN
    DELETE FROM places_fts WHERE rowid = old.id;
END;

CREATE TRIGGER places_au AFTER UPDATE ON places BEGIN
    DELETE FROM places_fts WHERE rowid = old.id;
    INSERT INTO places_fts(rowid, name, name_am, name_sid, aliases)
    VALUES (
        new.id,
        new.name,
        new.name_am,
        new.name_sid,
        (SELECT group_concat(alias, ' ') FROM aliases WHERE place_id = new.id)
    );
END;

CREATE TRIGGER aliases_ai AFTER INSERT ON aliases BEGIN
    UPDATE places_fts
    SET aliases = (SELECT group_concat(alias, ' ') FROM aliases WHERE place_id = new.place_id)
    WHERE rowid = new.place_id;
END;

CREATE TRIGGER aliases_ad AFTER DELETE ON aliases BEGIN
    UPDATE places_fts
    SET aliases = (SELECT group_concat(alias, ' ') FROM aliases WHERE place_id = old.place_id)
    WHERE rowid = old.place_id;
END;

CREATE TRIGGER aliases_au AFTER UPDATE ON aliases BEGIN
    UPDATE places_fts
    SET aliases = (SELECT group_concat(alias, ' ') FROM aliases WHERE place_id = new.place_id)
    WHERE rowid = new.place_id;
END;
