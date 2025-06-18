
from google.adk.agents import Agent

appointment_agent = Agent(
    name="appointment_agent",
    description="Finds and books appointments with doctors.",
    instruction="You are an AI assistant that helps users find appropriate doctors based on their symptoms and location, and assists with booking an appointment."
)