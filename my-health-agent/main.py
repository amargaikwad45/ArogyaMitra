import asyncio
import uuid
import re
import random
import getpass

from db.user_profile_db import (
    initialize_user_database, add_user, get_user, verify_password
)

from orchestrator_agent.agent import root_agent as orchestrator_agent
from orchestrator_agent.sub_agents.appointment_agent.database import initialize_database

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from utils import add_user_query_to_history, call_agent_async

load_dotenv()

# MODIFIED: This function now takes the username as an argument and gathers only the remaining details.
def gather_health_profile(user_name: str):
    """Interactively gathers the rest of the health profile after name/password are set."""
    print("\n--- Please Complete Your Health Profile ---")
    
    age_input = input("🎂 What is your age? > ").strip()
    age = int(age_input) if age_input.isdigit() else None

    sex = input("🚻 What is your sex (e.g., Male, Female)? > ").strip()

    print("\n🩺 Please list any diagnosed conditions, separated by a comma (e.g., Asthma, Hypertension).")
    conditions_input = input("> ")
    diagnosed_conditions = [cond.strip() for cond in conditions_input.split(',') if cond.strip()]

    print("\n💊 Please add your current medications (press Enter to finish).")
    current_medications = []
    while True:
        med_name = input("   - Medication Name: > ").strip()
        if not med_name: break
        med_dosage = input(f"     - Dosage for {med_name}: > ").strip()
        current_medications.append({"name": med_name, "dosage": med_dosage})

    user_profile_state = {
        "user_context": {
            "user_name": user_name, # Uses the name passed into the function
            "personalInfo": {"age": age, "sex": sex},
            "diagnosedConditions": diagnosed_conditions,
            "currentMedications": current_medications,
        },
        "interaction_history": [],
    }
    return user_profile_state

def display_user_profile(user_state):
    """Prints a formatted summary of the user's profile from the state."""
    print("\n--- Your Health Profile ---")
    context = user_state.get("user_context", {})
    if not context:
        print("Could not load profile details.")
        return

    print(f"👤 Name: {context.get('user_name', 'N/A')}")
    personal_info = context.get('personalInfo', {})
    age = personal_info.get('age', 'N/A')
    sex = personal_info.get('sex', 'N/A')
    print(f"📋 Details: Age: {age}, Sex: {sex}")

    conditions = context.get('diagnosedConditions', [])
    if conditions:
        print(f"🩺 Diagnosed Conditions: {', '.join(conditions)}")
    else:
        print("🩺 Diagnosed Conditions: None listed.")

    meds = context.get('currentMedications', [])
    if meds:
        print("💊 Current Medications:")
        for med in meds:
            print(f"   - {med.get('name', 'N/A')} ({med.get('dosage', 'N/A')})")
    else:
        print("💊 Current Medications: None listed.")
    print("---------------------------\n")


def login_flow():
    """Handles the login process for an existing user."""
    print("\n--- User Login ---")
    username = input("Enter your full name: > ").strip()
    password = getpass.getpass("Enter your 4-digit password: > ").strip()

    profile_data, stored_hash = get_user(username)
    
    if profile_data and verify_password(stored_hash, password):
        print("\n✅ Login successful!")
        return username, profile_data
    else:
        print("\n❌ Login failed. Please check your name or password.")
        return None, None

# MODIFIED: This function now follows the Name -> Password -> Details flow.
def register_flow():
    """Handles the registration process for a new user."""
    print("\n--- New User Registration ---")
    
    # Step 1: Get the username
    username = input("👤 What is your full name? > ").strip()
    if not username:
        print("Name cannot be empty.")
        return None, None
        
    # Step 2: Get and confirm the password
    password = ""
    while True:
        p1 = getpass.getpass("🔑 Please choose a 4-digit password: > ").strip()
        if not (p1.isdigit() and len(p1) == 4):
            print("   Invalid input. Password must be exactly 4 digits.")
            continue

        p2 = getpass.getpass("🔑 Please confirm your password: > ").strip()
        if p1 == p2:
            password = p1
            break
        else:
            print("   Passwords do not match. Please try again.")
    
    # Step 3: Get the rest of the health profile
    profile_data = gather_health_profile(username)
    
    # Step 4: Save everything to the database
    if add_user(username, password, profile_data):
        print("\n✅ Registration successful! Your profile has been saved.")
        return username, profile_data
    else:
        # add_user prints its own error message (e.g., username taken)
        return None, None

async def main_async():
    # Initialize both databases
    initialize_user_database()
    initialize_database()

    user_state = None
    username = None
    
    # Loop until a user is successfully logged in or registered
    while not user_state:
        choice = input("\nWelcome to Arogya Mitra!\n1. Login\n2. Register\n3. Exit\n> ").strip()
        if choice == '1':
            username, user_state = login_flow()
        elif choice == '2':
            username, user_state = register_flow()
        elif choice == '3':
            return
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

    # Display the user's profile right after successful login/registration.
    display_user_profile(user_state)

    APP_NAME = "Arogya Mitra"
    # Create a safe and consistent USER_ID from the username
    USER_ID = re.sub(r'\W+', '_', username).lower()

    session_service = DatabaseSessionService(db_url="sqlite:///./arogyamitra.db")

    list_sessions_response = session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)

    if list_sessions_response.sessions:
        session_id = list_sessions_response.sessions[0].id
        print(f"Continuing your previous chat session...")
    else:
        session_id = str(uuid.uuid4())
        session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id, state=user_state)
        print(f"Created a new chat session for you.")

    runner = Runner(agent=orchestrator_agent, app_name=APP_NAME, session_service=session_service)
    
    print("\n--- Arogya Mitra Health Assistant ---")
    print("Type 'view my appointments', ask about symptoms, or book a new appointment.")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input(f"{username}: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Ending conversation. Goodbye! Your session is saved.")
            break
        add_user_query_to_history(session_service, APP_NAME, USER_ID, session_id, user_input)
        await call_agent_async(runner, USER_ID, session_id, user_input)

def main():
    """Entry point for the application."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nExiting application.")

if __name__ == "__main__":
    main()