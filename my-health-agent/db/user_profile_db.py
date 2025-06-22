# my-health-agent/db/user_profile_db.py
import sqlite3
import json
import hashlib
import random
from pathlib import Path

# Place this database in the project's root `db` directory
DB_FILE = Path(__file__).parent / "user_profiles.db"

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    except sqlite3.Error as e:
        print(e)
    return conn

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verifies a provided password against a stored hash."""
    return stored_hash == hash_password(provided_password)

def create_user_table(conn):
    """Create the users table if it doesn't exist."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                profile_json TEXT NOT NULL
            );
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating user table: {e}")

def add_user(username, password, profile_data) -> bool:
    """Adds a new user to the database with a hashed password."""
    conn = create_connection()
    if not conn: return False
    
    hashed_pass = hash_password(password)
    profile_str = json.dumps(profile_data)
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password_hash, profile_json) VALUES (?, ?, ?)",
            (username, hashed_pass, profile_str)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # This error occurs if the username is already taken
        print(f"Error: Username '{username}' already exists.")
        return False
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_user(username: str):
    """Retrieves a user's profile and hashed password from the database."""
    conn = create_connection()
    if not conn: return None, None

    cursor = conn.cursor()
    cursor.execute("SELECT profile_json, password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        profile_data = json.loads(row[0])
        password_hash = row[1]
        return profile_data, password_hash
    
    return None, None

def initialize_user_database():
    """Initializes the user database and creates the necessary table."""
    print("Initializing user profile database...")
    conn = create_connection()
    if conn:
        create_user_table(conn)
        conn.close()
        print("User profile database is ready.")