# clipmato/cli/gui.py
from .pipeline import run_pipeline
from .ui import make_gui_app

def run():
    app = make_gui_app(run_pipeline)
    app.mainloop()

if __name__ == "__main__":
    run()