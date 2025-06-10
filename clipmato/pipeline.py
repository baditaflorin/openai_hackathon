"""
Run the full Clipmato production pipeline or import individual steps programmatically.
"""
from .cli.pipeline import run_pipeline, main

if __name__ == "__main__":
    main()