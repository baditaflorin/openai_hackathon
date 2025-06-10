from .pipeline import run_pipeline
from .ui import make_gui_app

if __name__ == "__main__":
    app = make_gui_app(run_pipeline)
    app.mainloop()