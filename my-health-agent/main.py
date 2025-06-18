# main.py
import asyncio

# ADAPTED: Import the orchestrator agent for the health app
from orchestrator_agent.agent import root_agent as orchestrator_agent

from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from utils import add_user_query_to_history, call_agent_async

load_dotenv()

# Using in-memory storage, conversation state will be lost on exit
session_service = InMemorySessionService()


# ADAPTED: Define the initial state for a new user in the health app
# This context would typically be populated by processing a medical report
initial_state = {
    "user_context": {
        "user_name": "Ravi Kumar",
        "personalInfo": {"age": 45, "sex": "Male"},
        "diagnosedConditions": ["Type 2 Diabetes", "Hypertension"],
        "currentMedications": [{"name": "Metformin", "dosage": "500mg"}],
    },
    "interaction_history": [],
}


async def main_async():
    # ADAPTED: Setup constants for the health app
    APP_NAME = "Arogya Mitra"
    USER_ID = "sample user"

    # Create a new session with the initial health context
    new_session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state=initial_state,
    )
    SESSION_ID = new_session.id
    print(f"Created new session for {USER_ID}: {SESSION_ID}")

    # ADAPTED: Create a runner with our main orchestrator agent
    runner = Runner(
        agent=orchestrator_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # --- Interactive Conversation Loop (Identical to your example) ---
    print("\nWelcome to the Arogya Mitra Health Assistant!")
    print("You can ask about symptoms, fitness, or general health questions.")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Ending conversation. Goodbye!")
            break

        # Update interaction history with the user's query
        add_user_query_to_history(
            session_service, APP_NAME, USER_ID, SESSION_ID, user_input
        )

        # Process the user query through the agent
        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)

    # --- Final State Examination (Identical to your example) ---
    final_session = session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    print("\nFinal Session State:")
    # Pretty print the final state
    import json
    print(json.dumps(final_session.state, indent=2))


def main():
    """Entry point for the application."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()