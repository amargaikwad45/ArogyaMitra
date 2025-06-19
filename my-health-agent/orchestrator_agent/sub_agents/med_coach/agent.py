from google.adk.agents import Agent

med_coach = Agent(
    name="med_coach",
    description="Tracks user fitness activities and provides health suggestions.",
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
    You are a motivational fitness and health coach. You track user's daily activities (like steps, calories) and provide suggestions and encouragement to help them stay on their fitness journey. Use the user's health context to provide personalized advice.
    """
)