import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "redmes.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")
    
    with get_connection() as conn:
        with open(SCHEMA_PATH, 'r') as f:
            conn.executescript(f.read())
        conn.commit()

def get_contact_id(name: str, create_if_missing: bool = True) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contacts WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        
        if create_if_missing:
            cursor.execute("INSERT INTO contacts (name) VALUES (?)", (name,))
            conn.commit()
            return cursor.lastrowid
        return None

def fetch_contact_history(name: str):
    contact_id = get_contact_id(name, create_if_missing=False)
    if not contact_id:
        return []
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT raw_message, detected_tone, relationship_type, scenario, detected_language, output_language, risk_score, chosen_version, outcome, created_at
            FROM messages
            WHERE contact_id = ?
            ORDER BY created_at DESC
        ''', (contact_id,))
        return [dict(row) for row in cursor.fetchall()]

def insert_message_log(name: str, raw_message: str, detected_tone: str, relationship_type: str, scenario: str, detected_language: str, output_language: str, risk_score: int, chosen_version: str, outcome: str):
    contact_id = get_contact_id(name, create_if_missing=True)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (contact_id, raw_message, detected_tone, relationship_type, scenario, detected_language, output_language, risk_score, chosen_version, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (contact_id, raw_message, detected_tone, relationship_type, scenario, detected_language, output_language, risk_score, chosen_version, outcome))
        conn.commit()
        return cursor.lastrowid
