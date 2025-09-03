import tkinter as tk
from tkinter import messagebox
import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from audio import AudioPlayer
from brightness import Backlight
from rtc_sync import RTC
from gpio_buttons import GpioButtons


CONFIG_FILE = "config.json"


class AlarmClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Relógio com Alarme")
        self.root.attributes("-fullscreen", True)

        # Inicializações
        self.audio = AudioPlayer()
        self.buttons = GpioButtons(callback=self.handle_gpio)
        self.buttons.start()

        self.alarms = []
        self.load_config()

        # Widgets
        self.time_label = tk.Label(
            root, text="", font=("Helvetica", 72), fg="white", bg="black"
        )
        self.time_label.pack(expand=True, fill="both")

        self.status_label = tk.Label(
            root, text="", font=("Helvetica", 20), fg="yellow", bg="black"
        )
        self.status_label.pack(side="bottom", fill="x")

        # Thread de checagem de alarmes
        self.running = True
        self.alarm_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.alarm_thread.start()

        self.update_clock()

    def load_config(self):
        if not Path(CONFIG_FILE).exists():
            # cria config padrão
            default_cfg = {
                "alarms": [],
                "snooze_minutes": 10,
                "brightness": 180,
                "auto_dim": {"enabled": False, "night": 40, "start": "22:30", "end": "06:30"},
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_cfg, f, indent=2)

        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            self.alarms = cfg.get("alarms", [])
            self.snooze_minutes = cfg.get("snooze_minutes", 10)
            self.brightness = cfg.get("brightness", 180)
            self.auto_dim = cfg.get("auto_dim", {})

        Backlight.set(self.brightness)

    def save_config(self):
        cfg = {
            "alarms": self.alarms,
            "snooze_minutes": self.snooze_minutes,
            "brightness": self.brightness,
            "auto_dim": self.auto_dim,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)

    def update_clock(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def check_alarms(self):
        while self.running:
            now = datetime.now()
            for alarm in self.alarms:
                if not alarm.get("enabled", False):
                    continue

                if now.strftime("%H:%M") == alarm["time"]:
                    # Checa se o dia da semana bate
                    weekday = now.weekday()  # 0 = seg
                    if weekday in alarm.get("days", []):
                        self.trigger_alarm(alarm)

            time.sleep(30)  # checa a cada 30s

    def trigger_alarm(self, alarm):
        sound = alarm.get("sound", "assets/alarm.mp3")
        volume = alarm.get("volume", 70)
        AudioPlayer.set_volume(volume)
        self.audio.play(sound, loop=True)
        self.status_label.config(text=f"Alarme: {alarm.get('label', '')}")

    def handle_gpio(self, event):
        if event == "snooze":
            self.snooze_alarm()
        elif event == "stop":
            self.stop_alarm()

    def snooze_alarm(self):
        self.audio.stop()
        self.status_label.config(text="Soneca ativada")
        threading.Thread(target=self._snooze_wait, daemon=True).start()

    def _snooze_wait(self):
        time.sleep(self.snooze_minutes * 60)
        self.status_label.config(text="Soneca terminou")
        # Reproduz de novo o último alarme
        if self.alarms:
            self.trigger_alarm(self.alarms[0])

    def stop_alarm(self):
        self.audio.stop()
        self.status_label.config(text="Alarme parado")

    def on_close(self):
        self.running = False
        self.buttons.stop()
        self.audio.stop()
        self.save_config()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmClockApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
