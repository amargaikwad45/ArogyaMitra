import sqlite3
import json
from pathlib import Path
from faker import Faker
import random

DB_FILE = Path(__file__).parent / "doctors.db"

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    except sqlite3.Error as e:
        print(e)
    return conn

def create_tables(conn):
    """Create doctors and appointments tables."""
    try:
        cursor = conn.cursor()
        # Doctor Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                specialization TEXT NOT NULL,
                experience_years INTEGER,
                location TEXT,
                hospital_name TEXT,
                consultation_fee REAL,
                visiting_hours TEXT
            );
        """)
        # Appointments Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                patient_name TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Booked',
                FOREIGN KEY (doctor_id) REFERENCES doctors (id)
            );
        """)
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

def generate_and_populate_doctors(conn, count=1000):
    """Populate the doctors table with generated data using Faker if it's empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] > 0:
        print("Doctor database already populated.")
        return

    print(f"Database is empty. Generating {count} new doctor records...")
    fake = Faker('en_IN') # Use Indian locale for names/locations

    specializations = ['Cardiologist', 'Neurologist', 'Dermatologist', 'Orthopedic Surgeon', 'General Physician', 'Pediatrician', 'Oncologist', 'Endocrinologist', 'Gastroenterologist']
    locations = ['Mumbai', 'Delhi', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad', 'Pune', 'Ahmedabad']
    hospitals = ["City Hospital", "Apollo Clinic", "Fortis Health", "Manipal Center", "Max Healthcare", "Global Medical", "Sunrise Institute"]
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    doctors_data = []
    for _ in range(count):
        spec = random.choice(specializations)
        name = f"Dr. {fake.first_name()} {fake.last_name()}"
        exp = random.randint(5, 25)
        loc = random.choice(locations)
        hosp = f"{random.choice(hospitals)}, {loc}"
        fee = random.randint(8, 25) * 100
        
        # Generate visiting hours
        start_hour = random.randint(9, 14)
        end_hour = start_hour + random.randint(2, 4)
        visiting_days = sorted(random.sample(days, k=random.randint(3, 5)))
        hours = {",".join(visiting_days): f"{start_hour:02d}:00-{end_hour:02d}:00"}

        doctors_data.append((name, spec, exp, loc, hosp, fee, json.dumps(hours)))

    cursor.executemany("""
        INSERT INTO doctors (name, specialization, experience_years, location, hospital_name, consultation_fee, visiting_hours)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, doctors_data)
    conn.commit()
    print(f"Successfully populated database with {count} doctors.")

def _find_doctors_in_db(specialization: str, location: str):
    """Searches for doctors based on medical specialization and location. For example, 'find a physician in Mumbai'. Returns a list of the top 5 matching doctors with their details.

    Args:
        specialization: The medical field of the doctor (e.g., 'Cardiologist', 'Physician').
        location: The city where the user is looking for a doctor (e.g., 'Mumbai', 'Delhi').
    """
    conn = create_connection()
    if not conn:
        return "Error: Could not connect to the database."
    
    cursor = conn.cursor()
    query = "SELECT id, name, specialization, experience_years, hospital_name, consultation_fee, visiting_hours FROM doctors WHERE 1=1"
    params = []
    
    if specialization:
        search_term = 'General Physician' if 'physician' in specialization.lower() else specialization
        query += " AND specialization LIKE ?"
        params.append(f"%{search_term}%")
    if location:
        query += " AND location LIKE ?"
        params.append(f"%{location}%")
    
    query += " ORDER BY experience_years DESC LIMIT 5"
        
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No doctors found matching your criteria. Please try a different specialization or location."
        
    results = []
    for row in rows:
        results.append({
            "id": row[0], "name": row[1], "specialization": row[2],
            "experience_years": row[3], "hospital_name": row[4],
            "consultation_fee": row[5], "visiting_hours": json.loads(row[6])
        })
    return json.dumps(results, indent=2)

def _book_appointment_in_db(doctor_id: int, patient_name: str, date: str, time: str):
    """Books an appointment with a specific doctor for a user.

    Args:
        doctor_id: The unique ID of the doctor, which is found using the find_doctors tool.
        patient_name: The full name of the patient for whom the appointment is booked.
        date: The desired date for the appointment in 'YYYY-MM-DD' or natural language format (e.g., 'tomorrow').
        time: The desired time for the appointment (e.g., '10 AM', '15:00').
    """
    conn = create_connection()
    if not conn:
        return "Error: Could not connect to the database."

    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, visiting_hours FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()
        if not doctor:
            conn.close()
            return f"Error: No doctor found with ID {doctor_id}."
        
        doctor_name = doctor[0]

        cursor.execute(
            "INSERT INTO appointments (doctor_id, patient_name, appointment_date, appointment_time) VALUES (?, ?, ?, ?)",
            (doctor_id, patient_name, date, time)
        )
        conn.commit()
        appointment_id = cursor.lastrowid
        conn.close()
        
        return json.dumps({
            "status": "Success",
            "message": "Appointment booked successfully!",
            "appointment_id": appointment_id,
            "doctor_name": doctor_name,
            "patient_name": patient_name,
            "date": date,
            "time": time
        })
    except sqlite3.Error as e:
        conn.close()
        return f"Error: Could not book appointment. Reason: {e}"

def initialize_database():
    """Initializes the database, creating tables and populating if needed."""
    print("Initializing doctor database...")
    conn = create_connection()
    if conn is not None:
        create_tables(conn)
        generate_and_populate_doctors(conn, 1000) # Generate 1000 doctors
        conn.close()
        print("Database ready.")
    else:
        print("Error! cannot create the database connection.")