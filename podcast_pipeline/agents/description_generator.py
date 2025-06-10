from agents import Agent

description_generator_agent = Agent(
    name="Description Generator",
    instructions="""
You are a podcast assistant that creates both a short and a long description for a given transcript.
Return a JSON object with the keys "short_description" (a one-sentence summary)
and "long_description" (a 3-4 sentence paragraph providing more detail).
""",
)