from agents import Agent

audio_editor_agent = Agent(
    name="Audio Editor",
    instructions="""
You are responsible for basic audio cleanup. Reply with a confirmation message when done.
""",
)
