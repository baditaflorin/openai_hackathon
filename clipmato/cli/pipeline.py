"""
Run the full Clipmato production pipeline or import individual steps programmatically.
"""
from ..steps import curate_content, generate_script, edit_audio, distribute
from .ui import run_cli

def run_pipeline():
    """Run the Clipmato production pipeline and return step outputs."""
    topic = curate_content("Find a trending tech topic")
    script = generate_script(topic)
    edited_audio = edit_audio("process raw audio")
    distribution = distribute(edited_audio)

    return {
        "topic": topic,
        "script": script,
        "edited_audio": edited_audio,
        "distribution": distribution,
    }

def main():
    """Run the Clipmato production pipeline in CLI mode."""
    run_cli(run_pipeline)

if __name__ == "__main__":
    main()