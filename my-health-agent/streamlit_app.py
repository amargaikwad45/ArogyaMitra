import streamlit as st
import asyncio
import uuid
import re
from pathlib import Path
import os

# Import necessary components from the current package structure
# The imports are now relative to the 'my-health-agent' directory
from db.user_profile_db import initialize_user_database, add_user, get_user, verify_password
from orchestrator_agent.agent import root_agent as orchestrator_agent
from orchestrator_agent.sub_agents.appointment_agent.database import initialize_database
from utils import add_user_query_to_history, call_agent_async # display_state function prints to console and won't be shown in UI

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from dotenv import load_dotenv

# --- Configuration ---
# Adjust path to your .env file which is in the parent directory of my-health-agent
load_dotenv(Path(__file__).parent.parent / '.env') 

APP_NAME = "Arogya Mitra"

# --- Initialization (Run once on app startup) ---
# Use st.cache_resource to ensure databases and runner are initialized only once
@st.cache_resource
def setup_databases_and_runner():
    """Initializes databases and sets up the ADK Runner."""
    print("Initializing user profile database...") # These will print to the console where Streamlit runs
    initialize_user_database()
    print("Initializing doctor database...")
    initialize_database()

    # Set up the session service and runner
    # The database file (arogyamitra.db) will be created in the directory where you run streamlit_app.py
    session_service = DatabaseSessionService(db_url="sqlite:///./arogyamitra.db")
    runner = Runner(agent=orchestrator_agent, app_name=APP_NAME, session_service=session_service)
    return session_service, runner

session_service, runner = setup_databases_and_runner()

# --- Streamlit Session State Management ---
# Initialize session state variables for persistence across reruns
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Helper Functions for UI Integration ---

def gather_health_profile_ui(username_val):
    """Gathers health profile details from Streamlit UI inputs."""
    st.subheader("Complete Your Health Profile")
    age = st.text_input("What is your age?", key="reg_age_input")
    sex = st.text_input("What is your sex (e.g., Male, Female)?", key="reg_sex_input")
    conditions = st.text_area("Please list any diagnosed conditions, separated by a comma (e.g., Asthma, Hypertension).", key="reg_cond_input")
    medications_input = st.text_area("Please add your current medications (one per line, format: Name (Dosage)).", key="reg_meds_input")

    diagnosed_conditions = [c.strip() for c in conditions.split(',') if c.strip()]
    current_medications = []
    for line in medications_input.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r"(.+)\((.+)\)", line)
            if match:
                current_medications.append({"name": match.group(1).strip(), "dosage": match.group(2).strip()})
            else:
                current_medications.append({"name": line, "dosage": "N/A"}) # Default if no dosage in parens

    profile_data = {
        "user_context": {
            "user_name": username_val,
            "personalInfo": {"age": int(age) if age.isdigit() else None, "sex": sex},
            "diagnosedConditions": diagnosed_conditions,
            "currentMedications": current_medications,
        },
        "interaction_history": [],
    }
    return profile_data, age, sex, conditions, medications_input # Return all inputs to check if they are empty later

# --- Login/Registration UI ---
if not st.session_state.logged_in:
    st.title("Welcome to Arogya Mitra!")
    st.write("Please Login or Register to continue.")

    auth_choice = st.radio("Choose action", ["Login", "Register"], horizontal=True)

    if auth_choice == "Login":
        with st.form("login_form"):
            username_login = st.text_input("Full Name")
            password_login = st.text_input("4-digit Password", type="password", max_chars=4)
            submitted = st.form_submit_button("Login")

            if submitted:
                if not username_login or not password_login:
                    st.error("Please enter both username and password.")
                else:
                    profile_data, stored_hash = get_user(username_login)
                    if profile_data and verify_password(stored_hash, password_login):
                        st.session_state.logged_in = True
                        st.session_state.username = username_login
                        st.session_state.user_profile = profile_data
                        st.session_state.user_id = re.sub(r'\W+', '_', username_login).lower()

                        # Load existing session or create a new one
                        list_sessions_response = session_service.list_sessions(app_name=APP_NAME, user_id=st.session_state.user_id)
                        if list_sessions_response.sessions:
                            st.session_state.session_id = list_sessions_response.sessions[0].id
                            # Reload history for display if continuing session
                            current_session_state = session_service.get_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id)
                            st.session_state.chat_history = current_session_state.state.get("interaction_history", [])
                            st.success("Login successful! Continuing your previous chat session.")
                        else:
                            st.session_state.session_id = str(uuid.uuid4())
                            session_service.create_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id, state=st.session_state.user_profile)
                            st.success("Login successful! Created a new chat session for you.")
                        st.rerun() # Rerun to display chat interface
                    else:
                        st.error("Login failed. Please check your name or password.")

    elif auth_choice == "Register":
        with st.form("register_form"):
            username_reg = st.text_input("Full Name")
            password_reg = st.text_input("4-digit Password", type="password", max_chars=4)
            password_confirm_reg = st.text_input("Confirm Password", type="password", max_chars=4)
            
            # Use a button to trigger profile data gathering and registration
            submitted_reg = st.form_submit_button("Proceed to Health Profile / Register")

            if submitted_reg:
                if not username_reg:
                    st.error("Name cannot be empty.")
                elif not (password_reg.isdigit() and len(password_reg) == 4):
                    st.error("Password must be exactly 4 digits.")
                elif password_reg != password_confirm_reg:
                    st.error("Passwords do not match.")
                else:
                    st.session_state.reg_username = username_reg
                    st.session_state.reg_password = password_reg
                    st.session_state.show_profile_form = True # Flag to show health profile form

        if st.session_state.get('show_profile_form', False):
            with st.form("health_profile_form"):
                profile_data_temp, age, sex, conditions, medications_input = gather_health_profile_ui(st.session_state.reg_username)
                register_button = st.form_submit_button("Register Account")

                if register_button:
                    # Basic validation for profile fields
                    if not age or not sex or not conditions or not medications_input:
                        st.error("Please fill in all health profile details.")
                    else:
                        if add_user(st.session_state.reg_username, st.session_state.reg_password, profile_data_temp):
                            st.session_state.logged_in = True
                            st.session_state.username = st.session_state.reg_username
                            st.session_state.user_profile = profile_data_temp
                            st.session_state.user_id = re.sub(r'\W+', '_', st.session_state.reg_username).lower()
                            st.session_state.session_id = str(uuid.uuid4())
                            session_service.create_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id, state=st.session_state.user_profile)
                            st.success("Registration successful! Your profile has been saved.")
                            st.session_state.chat_history = [] # New user, empty chat history
                            st.session_state.show_profile_form = False # Hide form after registration
                            st.rerun() # Rerun to display chat interface
                        else:
                            st.error(f"Registration failed. Username '{st.session_state.reg_username}' might already exist.")
                            st.session_state.show_profile_form = False # Hide form if registration fails

else:
    # --- Chat Interface (after successful login/registration) ---
    st.title(f"Arogya Mitra for {st.session_state.username}")

    # Display previous chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask Arogya Mitra..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call agent
        with st.chat_message("assistant"):
            with st.spinner("Arogya Mitra is thinking..."):
                # Call the async agent function using asyncio.run
                # Note: The 'display_state' and some print statements from utils.py
                # will output to the console where Streamlit is running, not directly in the UI.
                final_response = asyncio.run(
                    call_agent_async(
                        runner,
                        st.session_state.user_id,
                        st.session_state.session_id,
                        prompt
                    )
                )
            
            # Display the final response from the agent and add to chat history
            if final_response:
                st.markdown(final_response)
                st.session_state.chat_history.append({"role": "assistant", "content": final_response})
            else:
                st.markdown("Arogya Mitra did not return a direct response. Please check the console for logs if issues persist.")
                st.session_state.chat_history.append({"role": "assistant", "content": "No direct response from agent."})
            st.rerun() # Rerun to update chat history in UI

    # Optional: Display user profile in an expandable section
    with st.expander("View/Update My Health Profile"):
        context = st.session_state.user_profile.get("user_context", {})
        if context:
            st.write(f"**Name:** {context.get('user_name', 'N/A')}")
            personal_info = context.get('personalInfo', {})
            st.write(f"**Age:** {personal_info.get('age', 'N/A')}, **Sex:** {personal_info.get('sex', 'N/A')}")
            conditions = context.get('diagnosedConditions', [])
            st.write(f"**Diagnosed Conditions:** {', '.join(conditions) if conditions else 'None listed.'}")
            meds = context.get('currentMedications', [])
            if meds:
                st.write("**Current Medications:**")
                for med in meds:
                    st.write(f"- {med.get('name', 'N/A')} ({med.get('dosage', 'N/A')})")
            else:
                st.write("**Current Medications:** None listed.")
        else:
            st.write("Could not load profile details.")

    # Logout button in sidebar
    st.sidebar.button("Logout", on_click=lambda: (
        st.session_state.clear(), # Clear all session state
        st.rerun() # Rerun to go back to login page
    ))