import tkinter as tk
from .pipeline import run_pipeline


def run():
    text.delete(1.0, tk.END)
    outputs = run_pipeline()
    for key, value in outputs.items():
        text.insert(tk.END, f"{key}: {value}\n\n")


root = tk.Tk()
root.title("Podcast Pipeline")

run_button = tk.Button(root, text="Run Pipeline", command=run)
run_button.pack(pady=10)

text = tk.Text(root, width=80, height=20)
text.pack()

root.mainloop()
