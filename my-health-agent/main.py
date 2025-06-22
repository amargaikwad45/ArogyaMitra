# main.py
import asyncio
import uuid

from orchestrator_agent.agent import root_agent as orchestrator_agent
from orchestrator_agent.sub_agents.appointment_agent.database import initialize_database

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from utils import add_user_query_to_history, call_agent_async

load_dotenv()

async def main_async():
    # Initialize the doctor database on startup
    initialize_database()

    # Create a database session service
    session_service = DatabaseSessionService(
        db_url="sqlite:///./arogyamitra.db"
    )

    # Define the initial state for a new user in the health app
    initial_state = {
        "user_context": {
            "user_name": "Ravi Kumar",
            "personalInfo": {"age": 45, "sex": "Male"},
            "diagnosedConditions": ["Type 2 Diabetes", "Hypertension"],
            "currentMedications": [{"name": "Metformin", "dosage": "500mg"}],
        },
        "interaction_history": [],
    }

    # Setup constants for the health app
    APP_NAME = "Arogya Mitra"
    USER_ID = "sample_user_ravi_kumar" # Use a consistent user ID for persistence

    # CORRECTED: The list_sessions method returns a response object.
    # We need to access the .sessions attribute of that object to get the list.
    list_sessions_response = session_service.list_sessions(
        app_name=APP_NAME,
        user_id=USER_ID
    )

    # CORRECTED: Check the .sessions attribute of the response object.
    if list_sessions_response.sessions:
        # Use the most recent existing session from the list.
        session_id = list_sessions_response.sessions[0].id
        print(f"Continuing existing session for user '{USER_ID}': {session_id}")
    else:
        # Create a new session if none exist.
        session_id = str(uuid.uuid4())
        session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=session_id,
            state=initial_state,
        )
        print(f"Created new session for user '{USER_ID}': {session_id}")


    # Create a runner with our main orchestrator agent
    runner = Runner(
        agent=orchestrator_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # --- Interactive Conversation Loop ---
    print("\nWelcome to the Arogya Mitra Health Assistant!")
    print("Your conversation is now persistent and will be saved.")
    print("You can ask about symptoms, fitness, or book appointments.")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Ending conversation. Goodbye! Your session is saved.")
            break

        add_user_query_to_history(
            session_service, APP_NAME, USER_ID, session_id, user_input
        )

        await call_agent_async(runner, USER_ID, session_id, user_input)

    # --- Final State Examination ---
    final_session = session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    print("\nFinal Session State:")
    import json
    print(json.dumps(final_session.state, indent=2))


def main():
    """Entry point for the application."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()