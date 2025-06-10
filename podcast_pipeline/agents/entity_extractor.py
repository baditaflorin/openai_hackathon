from agents import Agent

entity_extractor_agent = Agent(
    name="Entity Extractor",
    instructions="""
You extract referenced people and locations from the podcast transcript.
Return a JSON object with two keys: "people" (list of people's names)
and "locations" (list of place names). Use empty lists if none are found.
""",
)