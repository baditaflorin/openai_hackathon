from agents import Agent

title_suggester_agent = Agent(
    name="Title Suggester",
    instructions="""
You suggest 5 catchy and descriptive podcast episode titles based on the provided transcript.
Return your suggestions as a JSON array of strings.
""",
)