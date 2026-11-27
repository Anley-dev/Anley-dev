-- Seed data for Hawassa core landmarks and POIs
-- 1. Menharya (Bus / Taxi Terminal & Commercial Area)
INSERT INTO places (id, name, name_am, name_sid, type, latitude, longitude, kebele)
VALUES (1, 'Menharya', 'መናኸሪያ', 'Menharya', 'transit', 7.0504, 38.4763, 'Menharya');

-- 2. Kebele 05
INSERT INTO places (id, name, name_am, name_sid, type, latitude, longitude, kebele)
VALUES (2, '05 Kebele', '05 ቀበሌ', '05 Kiffale', 'kebele', 7.0620, 38.4850, '05');

-- 3. Piazza
INSERT INTO places (id, name, name_am, name_sid, type, latitude, longitude, kebele)
VALUES (3, 'Piazza', 'ፒያሳ', 'Piazza', 'landmark', 7.0583, 38.4720, 'Piazza');

-- 4. Hawassa University (Main Campus)
INSERT INTO places (id, name, name_am, name_sid, type, latitude, longitude, kebele)
VALUES (4, 'Hawassa University (Main Campus)', 'ሐዋሳ ዩኒቨርሲቲ (ዋና ግቢ)', 'Hawaasi Yuniversite', 'university', 7.0531, 38.4947, 'Hawassa University');

-- 5. Hawassa Comprehensive Specialized Referral Hospital
INSERT INTO places (id, name, name_am, name_sid, type, latitude, longitude, kebele)
VALUES (5, 'Hawassa Referral Hospital', 'ሐዋሳ ሪፈራል ሆስፒታል', 'Hawaasi Referaale Hospitaale', 'hospital', 7.0458, 38.4886, 'Referral');

-- Multilingual aliases & transliterations
-- Menharya
INSERT INTO aliases (place_id, alias, language) VALUES (1, 'Menharya', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (1, 'Minariya', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (1, 'መናኸሪያ', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (1, 'መናሀሪያ', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (1, 'Menahariya', 'sid');

-- 05 Kebele
INSERT INTO aliases (place_id, alias, language) VALUES (2, '05', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (2, 'Amist', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (2, 'አምስት', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (2, '05 ቀበሌ', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (2, 'Kebele 05', 'en');

-- Piazza
INSERT INTO aliases (place_id, alias, language) VALUES (3, 'Piazza', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (3, 'Piassa', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (3, 'ፒያሳ', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (3, 'Piyasa', 'sid');

-- Hawassa University
INSERT INTO aliases (place_id, alias, language) VALUES (4, 'Hawassa University', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (4, 'HU', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (4, 'ሐዋሳ ዩኒቨርሲቲ', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (4, 'Main Campus', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (4, 'Hawaasi Yuniversite', 'sid');

-- Hawassa Referral Hospital
INSERT INTO aliases (place_id, alias, language) VALUES (5, 'Hawassa Referral Hospital', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (5, 'Referral Hospital', 'en');
INSERT INTO aliases (place_id, alias, language) VALUES (5, 'ሐዋሳ ሪፈራል ሆስፒታል', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (5, 'ሪፈራል', 'am');
INSERT INTO aliases (place_id, alias, language) VALUES (5, 'Referral', 'en');

-- Taxi and Bajaj Stations
INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('Menharya Bajaj Station', '05', 7.0504, 38.4763, 15.0);

INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('Menharya Bajaj Station', 'Piazza', 7.0504, 38.4763, 15.0);

INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('Piazza Bajaj Station', 'Menharya', 7.0583, 38.4720, 15.0);

INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('Piazza Bajaj Station', 'Hawassa University', 7.0583, 38.4720, 20.0);

INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('05 Bajaj Station', 'Piazza', 7.0620, 38.4850, 15.0);

INSERT INTO taxi_stations (name, destination, latitude, longitude, avg_fare_etb)
VALUES ('05 Bajaj Station', 'Referral Hospital', 7.0620, 38.4850, 20.0);
