"""
Run the full podcast production pipeline or import individual steps programmatically.
"""
from ..steps import curate_content, generate_script, edit_audio, distribute

def run_pipeline():
    """Run the podcast production pipeline and return step outputs."""
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
    """Run the podcast production pipeline."""
    outputs = run_pipeline()
    for key, value in outputs.items():
        print(f"{key}: {value}\n")

if __name__ == "__main__":
    main()