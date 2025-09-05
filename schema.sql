CREATE TABLE IF NOT EXISTS location (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    image_path TEXT,
    tags TEXT
);

CREATE TABLE IF NOT EXISTS cooler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    image_path TEXT,
    FOREIGN KEY(location_id) REFERENCES location(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cooler_id INTEGER NOT NULL,
    shift TEXT NOT NULL,
    temperature REAL NOT NULL,
    timestamp TEXT NOT NULL,
    signature TEXT NOT NULL,
    note TEXT,
    FOREIGN KEY(cooler_id) REFERENCES cooler(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
