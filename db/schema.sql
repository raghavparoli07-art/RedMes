CREATE TABLE IF NOT EXISTS contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id INTEGER NOT NULL,
  raw_message TEXT,
  detected_tone TEXT,
  relationship_type TEXT,
  scenario TEXT,
  detected_language TEXT,
  output_language TEXT,
  risk_score INTEGER,
  chosen_version TEXT,
  outcome TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (contact_id) REFERENCES contacts(id)
);
