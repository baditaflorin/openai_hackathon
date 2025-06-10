"""
UI glue for Clipmato CLI and GUI: formatting pipeline outputs,
and building CLI runner and Tkinter GUI application.
"""
import sys


def format_outputs(outputs: dict) -> str:
    """Format pipeline outputs as a human-readable string."""
    return "\n\n".join(f"{key}: {value}" for key, value in outputs.items())


def run_cli(run_fn):
    """Run the pipeline in CLI mode: execute run_fn and print formatted outputs."""
    outputs = run_fn()
    print(format_outputs(outputs))


def make_gui_app(run_fn):
    """Build and return a Tkinter root window for the pipeline GUI."""
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        sys.stderr.write(
            "Error: The tkinter module is not available. "
            "Please install Tcl/Tk support and refer to README.md for details.\n"
        )
        sys.exit(1)

    root = tk.Tk()
    root.title("Clipmato")

    def on_run():
        text.delete(1.0, tk.END)
        text.insert(tk.END, format_outputs(run_fn()))

    run_button = tk.Button(root, text="Run Pipeline", command=on_run)
    run_button.pack(pady=10)

    text = tk.Text(root, width=80, height=20)
    text.pack()

    return root