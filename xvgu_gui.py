import tkinter as tk
from tkinter import ttk
import subprocess
import threading  # For asynchronous buzzer control

# Common settings
colors = ["off", "hot_pink", "deep_pink", "white", "red", "yellow", "blue"]
patterns = ["ON", "OFF", "BLINK_1", "BLINK_2"]
layers = ["THREE", "TWO", "ONE"]

# Light execution function
def make_run_light(layer, color_var, pattern_var, status_label):
    def runner():
        color = color_var.get()
        pattern = pattern_var.get()
        try:
            subprocess.run([
                "python3", "xvgu.py", "ledset",
                "--layer", layer,
                "--name", color,
                "--pattern", pattern
            ], check=True)
            status_label.config(text="Success")
        except subprocess.CalledProcessError:
            status_label.config(text="Failed")
    return runner

# --- Buzzer control functions (tone + volume 対応) ---
def make_buzz_on(tone_var, volume_var):
    def run():
        cmd = ["python3", "xvgu.py", "buzzer"]
        tone = tone_var.get()
        volume = volume_var.get()
        if tone:
            cmd += ["--tone", tone]
        if volume:
            cmd += ["--volume", volume]
        subprocess.run(cmd)
    # 非同期で実行
    return lambda: threading.Thread(target=run, daemon=True).start()

def buzz_off():
    subprocess.run(["python3", "xvgu.py", "buzzer", "--off"])

# Build GUI
root = tk.Tk()
root.title("XVGU Controller")

# --- Light Control UI ---
for layer in layers:
    frame = tk.LabelFrame(root, text=f"Layer {layer} Control")
    frame.pack(padx=10, pady=5, fill="x")

    color_var = tk.StringVar(value="hot_pink")
    pattern_var = tk.StringVar(value="ON")

    ttk.Label(frame, text="Color:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(frame, textvariable=color_var, values=colors, width=12, state="readonly").grid(row=0, column=1)

    ttk.Label(frame, text="Pattern:").grid(row=0, column=2, sticky="w")
    ttk.Combobox(frame, textvariable=pattern_var, values=patterns, width=12, state="readonly").grid(row=0, column=3)

    status_label = tk.Label(frame, text="")
    status_label.grid(row=0, column=5, padx=10)

    tk.Button(
        frame,
        text="Run",
        command=make_run_light(layer, color_var, pattern_var, status_label)
    ).grid(row=0, column=4, padx=5)

# --- Buzzer Control UI ---
buzz_frame = tk.LabelFrame(root, text="Buzzer Control")
buzz_frame.pack(padx=10, pady=10, fill="x")

# Tone 選択（low / high）
tone_var = tk.StringVar(value="low")
ttk.Label(buzz_frame, text="Tone:").pack(side="left", padx=5)
ttk.Combobox(buzz_frame, textvariable=tone_var, values=["low", "high"], width=8, state="readonly").pack(side="left", padx=5)

# Volume 選択（big / mid / sml）
volume_var = tk.StringVar(value="mid")
ttk.Label(buzz_frame, text="Volume:").pack(side="left", padx=5)
ttk.Combobox(buzz_frame, textvariable=volume_var, values=["big", "mid", "sml"], width=8, state="readonly").pack(side="left", padx=5)

# ON / OFF ボタン
tk.Button(buzz_frame, text="ON", command=make_buzz_on(tone_var, volume_var), width=10).pack(side="left", padx=5)
tk.Button(buzz_frame, text="OFF", command=buzz_off, width=10).pack(side="left", padx=5)

root.mainloop()
