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

def onboard_new_user():
    """Interactively gathers profile information from a new user."""
    print("\n--- New User Registration ---")
    print("Let's set up your health profile.")

    user_name = input("👤 What is your full name? > ").strip()
    if not user_name:
        print("Name cannot be empty.")
        return None, None
    
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
            "user_name": user_name,
            "personalInfo": {"age": age, "sex": sex},
            "diagnosedConditions": diagnosed_conditions,
            "currentMedications": current_medications,
        },
        "interaction_history": [],
    }
    return user_name, user_profile_state

def login_flow():
    """Handles the login process for an existing user."""
    print("\n--- User Login ---")
    username = input("Enter your full name: > ").strip()
    password = getpass.getpass("Enter your 4-digit password: > ").strip()

    profile_data, stored_hash = get_user(username)
    
    if profile_data and verify_password(stored_hash, password):
        print("\n✅ Login successful! Loading your profile.")
        print(f"   Name: {profile_data['user_context']['user_name']}")
        print(f"   Conditions: {', '.join(profile_data['user_context']['diagnosedConditions'])}")
        return username, profile_data
    else:
        print("\n❌ Login failed. Please check your name or password.")
        return None, None

def register_flow():
    """Handles the registration process for a new user."""
    username, profile_data = onboard_new_user()
    if not username:
        return None, None

    # Generate a random 4-digit password
    password = str(random.randint(1000, 9999))
    
    if add_user(username, password, profile_data):
        print("\n✅ Registration successful!")
        print("="*40)
        print(f"  IMPORTANT: Your 4-digit password is: {password}")
        print("  Please save it. You will need it to log in next time.")
        print("="*40)
        return username, profile_data
    else:
        return None, None

async def main_async():
    # Initialize both databases
    initialize_user_database()
    initialize_database()

    user_state = None
    username = None
    
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

    APP_NAME = "Arogya Mitra"
    # Create a safe and consistent USER_ID from the username
    USER_ID = re.sub(r'\W+', '_', username).lower()

    session_service = DatabaseSessionService(db_url="sqlite:///./arogyamitra.db")

    list_sessions_response = session_service.list_sessions(app_name=APP_NAME, user_id=USER_ID)

    if list_sessions_response.sessions:
        session_id = list_sessions_response.sessions[0].id
        print(f"\nContinuing your previous session: {session_id}")
    else:
        session_id = str(uuid.uuid4())
        session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id, state=user_state)
        print(f"\nCreated a new chat session for you.")

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