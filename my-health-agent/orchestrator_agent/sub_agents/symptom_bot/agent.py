from google.adk.agents import Agent

symptom_bot = Agent(
    name="symptom_bot",
    description="Analyzes user's health symptoms to provide suggestions.",
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
    You are a helpful AI assistant that analyzes user's health symptoms. Ask clarifying questions to understand the symptoms fully before providing suggestions. If the user needs expert medical care, inform the orchestrator to redirect to the appointment agent.
    """
)