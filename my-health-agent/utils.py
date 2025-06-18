# utils.py
from datetime import datetime
from google.genai import types
import json

# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BG_BLUE = "\033[44m"
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"

async def process_agent_response(event):
    """Process and display agent response events."""
    print(f"Event ID: {event.id}, Author: {event.author}")

    # Check for specific parts first
    has_specific_part = False
    if event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, "text") and part.text and not part.text.isspace():
                print(f"  Text: '{part.text.strip()}'")

    # Check for final response after specific parts
    final_response = None
    if not has_specific_part and event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            final_response = event.content.parts[0].text.strip()
            # Use colors and formatting to make the final response stand out
            print(
                f"\n{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╔══ AGENT RESPONSE ═════════════════════════════════════════{Colors.RESET}"
            )
            print(f"{Colors.CYAN}{Colors.BOLD}{final_response}{Colors.RESET}")
            print(
                f"{Colors.BG_BLUE}{Colors.WHITE}{Colors.BOLD}╚═════════════════════════════════════════════════════════════{Colors.RESET}\n"
            )
        else:
            print(
                f"\n{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD}==> Final Agent Response: [No text content in final event]{Colors.RESET}\n"
            )

    return final_response

def add_user_query_to_history(session_service, app_name, user_id, session_id, query):
    """Adds a user query to the interaction history."""
    entry = {"role": "user", "content": query}
    _update_interaction_history(
        session_service, app_name, user_id, session_id, entry
    )


def add_agent_response_to_history(
    session_service, app_name, user_id, session_id, agent_name, response
):
    """Adds an agent response to the interaction history."""
    entry = {"role": agent_name, "content": response}
    _update_interaction_history(
        session_service, app_name, user_id, session_id, entry
    )


def _update_interaction_history(
    session_service, app_name, user_id, session_id, entry
):
    """Internal function to update the interaction history in state."""
    try:
        session = session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if not session:
            return

        # Get the history list from the session's state
        history = session.state.get("interaction_history", [])
        # Append the new entry
        history.append(entry)
        # The change is automatically reflected since we are modifying the object by reference
        
        # REMOVED: session_service.save_session(session) - This line was incorrect and is not needed.

    except Exception as e:
        print(f"{Colors.RED}Error updating interaction history: {e}{Colors.RESET}")


def display_state(session_service, app_name, user_id, session_id, label="Current State"):
    """Displays the current session state, adapted for the health app."""
    try:
        session = session_service.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if not session:
            print(f"{Colors.RED}Could not retrieve session to display state.{Colors.RESET}")
            return

        print(f"\n{Colors.YELLOW}{'-' * 10} {label} {'-' * 10}{Colors.RESET}")

        user_context = session.state.get("user_context", {})
        
        user_name = user_context.get("user_name", "Unknown User")
        print(f"👤 {Colors.BOLD}User:{Colors.RESET} {user_name}")

        personal_info = user_context.get("personalInfo", {})
        if personal_info:
            info_str = ", ".join(f"{k}: {v}" for k, v in personal_info.items())
            print(f"📋 {Colors.BOLD}Details:{Colors.RESET} {info_str}")

        conditions = user_context.get("diagnosedConditions", [])
        if conditions:
            print(f"🩺 {Colors.BOLD}Diagnosed Conditions:{Colors.RESET} {', '.join(conditions)}")
        
        meds = user_context.get("currentMedications", [])
        if meds:
            print(f"💊 {Colors.BOLD}Medications:{Colors.RESET}")
            for med in meds:
                print(f"   - {med.get('name', 'N/A')} ({med.get('dosage', 'N/A')})")

        interaction_history = session.state.get("interaction_history", [])
        if interaction_history:
            print(f"📝 {Colors.BOLD}Interaction History:{Colors.RESET}")
            for idx, entry in enumerate(interaction_history[-5:], 1):
                role = entry.get("role", "system")
                content = entry.get("content", "")
                if len(content) > 100:
                    content = content[:97] + "..."
                
                if role == "user":
                    print(f"   {idx}. {Colors.GREEN}User:{Colors.RESET} \"{content}\"")
                else:
                    print(f"   {idx}. {Colors.CYAN}{role}:{Colors.RESET} \"{content}\"")
        
        print(f"{Colors.YELLOW}{'-' * (22 + len(label))}{Colors.RESET}")

    except Exception as e:
        print(f"{Colors.RED}Error displaying state: {e}{Colors.RESET}")


async def call_agent_async(runner, user_id, session_id, query: str):
    """Calls the agent, streams the response, and displays state changes."""
    print(
        f"\n{Colors.BG_GREEN}{Colors.WHITE}{Colors.BOLD}--- Running Query: {query} ---{Colors.RESET}"
    )
    final_response_text = None
    agent_name = "agent"

    display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State BEFORE processing",
    )

    try:
        content = types.Content(role="user", parts=[types.Part(text=query)])
        
        print(f"{Colors.CYAN}{Colors.BOLD}Arogya Mitra:{Colors.RESET} ", end="", flush=True)
        async for chunk in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            if chunk.author:
                agent_name = chunk.author

            if chunk.content:
                print(chunk.content, end="", flush=True)

            if chunk.is_final_response and chunk.content:
                 final_response_text = process_agent_response(chunk)
                 
        print("\n")

    except Exception as e:
        print(f"{Colors.BG_RED}{Colors.WHITE} ERROR during agent run: {e} {Colors.RESET}")

    if final_response_text:
        add_agent_response_to_history(
            runner.session_service,
            runner.app_name,
            user_id,
            session_id,
            agent_name,
            final_response_text,
        )

    display_state(
        runner.session_service,
        runner.app_name,
        user_id,
        session_id,
        "State AFTER processing",
    )

    return final_response_text