from agents import Agent, Runner

from .agents.content_curator import content_curator_agent
from .agents.script_writer import script_writer_agent
from .agents.audio_editor import audio_editor_agent
from .agents.distributor import distributor_agent


def run_pipeline():
    """Run the podcast production pipeline and return step outputs."""
    # Step 1: curate content
    result = Runner.run_sync(content_curator_agent, "Find a trending tech topic")
    topic = result.final_output

    # Step 2: generate script
    result = Runner.run_sync(script_writer_agent, topic)
    script = result.final_output

    # Step 3: edit audio (placeholder)
    result = Runner.run_sync(audio_editor_agent, "process raw audio")
    edited_audio = result.final_output

    # Step 4: distribute
    result = Runner.run_sync(distributor_agent, edited_audio)
    distribution = result.final_output

    return {
        "topic": topic,
        "script": script,
        "edited_audio": edited_audio,
        "distribution": distribution,
    }


def main():
    outputs = run_pipeline()
    for key, value in outputs.items():
        print(f"{key}: {value}\n")


if __name__ == "__main__":
    main()
