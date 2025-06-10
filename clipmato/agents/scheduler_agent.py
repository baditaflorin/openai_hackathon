from agents import Agent

scheduler_agent = Agent(
    name="Scheduler Agent",
    instructions="""
You are a scheduling assistant. You receive a JSON object containing:
- "cadence": one of "daily", "weekly", or "every_n"
- "n_days": integer number of days for "every_n" (or null)
- "episodes": an array of objects with "id", "title", and "description"

Based on the cadence, assign each episode a posting datetime in ISO 8601 UTC.
Return a JSON object mapping episode IDs to ISO datetime strings.
""",
)