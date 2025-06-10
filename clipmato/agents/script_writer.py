from agents import Agent

script_writer_agent = Agent(
    name="Script Writer",
    instructions="""
You create concise show notes and interview questions for the provided topic.
Return a short paragraph and three questions.
""",
)
