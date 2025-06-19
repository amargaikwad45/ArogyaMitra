
from google.adk.agents import Agent

appointment_agent = Agent(
    name="appointment_agent",
    description="Finds and books appointments with doctors.",
    instruction="""
    
     **User Health Context:**
    This information is derived from the user's uploaded medical reports and ongoing interactions.
    <user_context>
    {user_context}
    </user_context>

    **Interaction History:**
    <interaction_history>
    {interaction_history}
    </interaction_history>

    You are an AI assistant that helps users find appropriate doctors based on their symptoms and location, and assists with booking an appointment.
    """
)