import streamlit as st
import asyncio
import uuid
import re
from pathlib import Path
import os

# Assuming these imports are correct for your project structure
from db.user_profile_db import initialize_user_database, add_user, get_user, verify_password
from orchestrator_agent.agent import root_agent as orchestrator_agent
from orchestrator_agent.sub_agents.appointment_agent.database import initialize_database
from utils import call_agent_async 

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from dotenv import load_dotenv

# --- Configuration ---
# Use an absolute path or a path relative to the script for robustness
load_dotenv(Path(__file__).resolve().parent.parent / '.env') 

APP_NAME = "Arogya Mitra"

# --- Initialization (Run once on app startup) ---
@st.cache_resource
def setup_databases_and_runner():
    """Initializes databases and sets up the ADK Runner."""
    print("Initializing user profile database...")
    initialize_user_database()
    print("Initializing doctor database...")
    initialize_database()

    session_db_path = "sqlite:///./arogyamitra_sessions.db"
    print(f"Initializing session service with DB at: {session_db_path}")
    session_service = DatabaseSessionService(db_url=session_db_path)
    runner = Runner(agent=orchestrator_agent, app_name=APP_NAME, session_service=session_service)
    return session_service, runner

session_service, runner = setup_databases_and_runner()

# --- Streamlit Session State Management ---
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
    """Gathers health profile details from Streamlit UI inputs and returns the profile data dictionary."""
    st.subheader("Complete Your Health Profile")
    age = st.text_input("What is your age?", key="reg_age_input")
    sex = st.selectbox("What is your sex?", ["Male", "Female", "Other", "Prefer not to say"], key="reg_sex_input")
    conditions = st.text_area("Please list any diagnosed conditions, separated by a comma (e.g., Asthma, Hypertension).", key="reg_cond_input")
    medications_input = st.text_area("Please add your current medications (one per line, format: Name (Dosage)).", key="reg_meds_input")

    # This function now only builds the data dict, validation happens outside
    diagnosed_conditions = [c.strip() for c in conditions.split(',') if c.strip()]
    current_medications = []
    for line in medications_input.split('\n'):
        line = line.strip()
        if line:
            match = re.match(r"(.+)\((.+)\)", line)
            if match:
                current_medications.append({"name": match.group(1).strip(), "dosage": match.group(2).strip()})
            else:
                current_medications.append({"name": line, "dosage": "N/A"})

    profile_data = {
        "user_context": {
            "user_name": username_val,
            "personalInfo": {"age": int(age) if age and age.isdigit() else None, "sex": sex},
            "diagnosedConditions": diagnosed_conditions,
            "currentMedications": current_medications,
        },
        "interaction_history": [],
    }
    # Return both the data and the raw inputs for validation
    return profile_data, age, sex, conditions, medications_input

# --- Login/Registration UI ---
if not st.session_state.logged_in:
    st.title("Welcome to Arogya Mitra!")
    st.write("Please Login or Register to continue.")

    auth_choice = st.radio("Choose action", ["Login", "Register"], horizontal=True, key="auth_choice")

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

                        list_sessions_response = session_service.list_sessions(app_name=APP_NAME, user_id=st.session_state.user_id)
                        if list_sessions_response.sessions:
                            st.session_state.session_id = list_sessions_response.sessions[0].id
                            current_session_state = session_service.get_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id)
                            st.session_state.chat_history = current_session_state.state.get("interaction_history", [])
                            st.success("Login successful! Continuing your previous chat session.")
                        else:
                            st.session_state.session_id = str(uuid.uuid4())
                            session_service.create_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id, state=st.session_state.user_profile)
                            st.success("Login successful! Created a new chat session for you.")
                        st.rerun() # Rerun here is GOOD - it transitions from login page to chat page
                    else:
                        st.error("Login failed. Please check your name or password.")

    elif auth_choice == "Register":
        # IMPROVED REGISTRATION FLOW: All in one form
        with st.form("register_form"):
            st.subheader("Create Your Account")
            username_reg = st.text_input("Full Name")
            password_reg = st.text_input("4-digit Password", type="password", max_chars=4)
            password_confirm_reg = st.text_input("Confirm Password", type="password", max_chars=4)
            
            # Gather health profile inside the same form
            profile_data, age, sex, conditions, meds = gather_health_profile_ui(username_reg)
            
            register_button = st.form_submit_button("Create Account & Login")

            if register_button:
                # --- Perform all validation at once ---
                if not username_reg or not password_reg:
                    st.error("Name and password cannot be empty.")
                elif not (password_reg.isdigit() and len(password_reg) == 4):
                    st.error("Password must be exactly 4 digits.")
                elif password_reg != password_confirm_reg:
                    st.error("Passwords do not match.")
                elif not all([age, sex, conditions, meds]):
                     st.error("Please fill in all health profile details.")
                else:
                    # --- All checks passed, attempt registration ---
                    if add_user(username_reg, password_reg, profile_data):
                        st.session_state.logged_in = True
                        st.session_state.username = username_reg
                        st.session_state.user_profile = profile_data
                        st.session_state.user_id = re.sub(r'\W+', '_', username_reg).lower()
                        st.session_state.session_id = str(uuid.uuid4())
                        session_service.create_session(app_name=APP_NAME, user_id=st.session_state.user_id, session_id=st.session_state.session_id, state=st.session_state.user_profile)
                        st.success("Registration successful! Your profile has been saved.")
                        st.session_state.chat_history = []
                        st.rerun() # Rerun here is GOOD - transitions from register page to chat page
                    else:
                        st.error(f"Registration failed. Username '{username_reg}' might already exist.")

else:
    # --- Chat Interface (after successful login/registration) ---
    st.title(f"Arogya Mitra for {st.session_state.username}")

    # Display previous chat messages from history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask Arogya Mitra..."):
        # Add user message to history and display it
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call agent and display response
        with st.chat_message("assistant"):
            with st.spinner("Arogya Mitra is thinking..."):
                try:
                    final_response = asyncio.run(
                        call_agent_async(
                            runner,
                            st.session_state.user_id,
                            st.session_state.session_id,
                            prompt
                        )
                    )
                except Exception as e:
                    st.error(f"An error occurred while contacting the agent: {e}")
                    final_response = "Sorry, I encountered an error. Please try again."

            # Display the final response from the agent and add to chat history
            st.markdown(final_response)
            st.session_state.chat_history.append({"role": "assistant", "content": final_response})

    # Optional: Display user profile in an expandable section
    with st.expander("View My Health Profile"):
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
    def logout():
        # Clear all session state keys
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    st.sidebar.button("Logout", on_click=logout)