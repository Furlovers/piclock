import tkinter as tk
from tkinter import messagebox
import json
import threading
import time
from datetime import datetime
from pathlib import Path

# --- GPIO e Buzzer ---
try:
    import RPi.GPIO as GPIO
    RPI_ENV = True
except ImportError:
    print(">>> Rodando em modo PC (sem Raspberry Pi). GPIO desativado.")
    RPI_ENV = False

    class GPIO:
        BCM = "BCM"
        OUT = "OUT"
        LOW = 0
        HIGH = 1
        @staticmethod
        def setmode(mode): print(f"[GPIO] setmode({mode})")
        @staticmethod
        def setwarnings(flag): pass
        @staticmethod
        def setup(pin, mode): print(f"[GPIO] setup(pin={pin}, mode={mode})")
        @staticmethod
        def output(pin, value): print(f"[GPIO] output(pin={pin}, value={value})")
        @staticmethod
        def cleanup(): print("[GPIO] cleanup()")


class AudioPlayer:
    buzzer_pins = [15, 18]   # agora dois pinos
    _is_playing = False

    @staticmethod
    def setup():
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in AudioPlayer.buzzer_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

    @staticmethod
    def play(volume=70):
        if AudioPlayer._is_playing:
            return
        AudioPlayer._is_playing = True
        threading.Thread(target=AudioPlayer._buzz, daemon=True).start()

    @staticmethod
    def stop():
        AudioPlayer._is_playing = False
        for pin in AudioPlayer.buzzer_pins:
            GPIO.output(pin, GPIO.LOW)

    @staticmethod
    def is_playing():
        return AudioPlayer._is_playing

    @staticmethod
    def _buzz():
        while AudioPlayer._is_playing:
            for pin in AudioPlayer.buzzer_pins:
                GPIO.output(pin, GPIO.HIGH)
            time.sleep(0.2)
            for pin in AudioPlayer.buzzer_pins:
                GPIO.output(pin, GPIO.LOW)
            time.sleep(0.2)


# --- App Principal ---
CONFIG_FILE = "config.json"


class AlarmClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Relógio com Alarme")
        self.root.geometry("800x480")  # ajuste para tela 7"
        self.root.resizable(False, False)
        self.root.configure(bg="#0a0a0a")

        self.colors = {
            "background": "#0a0a0a",
            "primary": "#00ffcc",
            "danger": "#ff5555",
            "success": "#55ff55",
            "warning": "#ffaa00",
            "text_secondary": "#cccccc",
        }

        self.alarms = []
        self.load_config()

        # Frame principal
        self.main_frame = tk.Frame(root, bg=self.colors["background"])
        self.main_frame.pack(expand=True, fill="both")

        # Data
        self.date_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 18),
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.date_label.pack(pady=(20, 0))

        # Hora
        self.time_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 72, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        self.time_label.pack(expand=True, pady=10)

        # Status
        self.status_label = tk.Label(
            self.main_frame,
            text="Nenhum alarme ativo",
            font=("Helvetica", 20),
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.status_label.pack(pady=5)

        # Próximo alarme
        self.next_alarm_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 14),
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.next_alarm_label.pack(pady=5)

        # Botões
        btn_frame = tk.Frame(self.main_frame, bg=self.colors["background"])
        btn_frame.pack(side="bottom", pady=20)

        self.test_button = tk.Button(
            btn_frame,
            text="Testar Alarme",
            command=self.test_alarm,
            font=("Helvetica", 16),
            width=14,
            bg="#222222",
            fg="white",
        )
        self.test_button.grid(row=0, column=0, padx=15)

        self.stop_button = tk.Button(
            btn_frame,
            text="Parar",
            command=self.stop_alarm,
            font=("Helvetica", 16),
            width=14,
            bg="#222222",
            fg="white",
        )
        self.stop_button.grid(row=0, column=1, padx=15)

        # Status visual (indicador)
        self.status_indicator = tk.Canvas(
            self.main_frame,
            width=25,
            height=25,
            bg=self.colors["background"],
            highlightthickness=0,
        )
        self.status_indicator.pack(pady=5)
        self.indicator = self.status_indicator.create_oval(
            3, 3, 22, 22, fill=self.colors["success"]
        )

        # Threads
        self.running = True
        self.alarm_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.alarm_thread.start()

        self.update_clock()

    def load_config(self):
        if not Path(CONFIG_FILE).exists():
            default_cfg = {
                "alarms": [],
                "snooze_minutes": 10,
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(default_cfg, f, indent=2)

        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
            self.alarms = cfg.get("alarms", [])
            self.snooze_minutes = cfg.get("snooze_minutes", 10)

    def save_config(self):
        cfg = {"alarms": self.alarms, "snooze_minutes": self.snooze_minutes}
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)

    def update_clock(self):
        now = datetime.now()
        self.date_label.config(text=now.strftime("%A, %d %B %Y"))
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def check_alarms(self):
        while self.running:
            now = datetime.now()
            for alarm in self.alarms:
                if not alarm.get("enabled", False):
                    continue
                if now.strftime("%H:%M") == alarm["time"]:
                    weekday = now.weekday()
                    if weekday in alarm.get("days", []):
                        self.trigger_alarm(alarm)
            time.sleep(30)

    def trigger_alarm(self, alarm):
        AudioPlayer.play()
        self.status_label.config(text=f"Alarme: {alarm.get('label','')}")
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["danger"])

    def stop_alarm(self):
        AudioPlayer.stop()
        self.status_label.config(text="Nenhum alarme ativo")
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["success"])

    def test_alarm(self):
        AudioPlayer.play()
        self.status_label.config(text="🔔 Testando alarme")
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["warning"])
        self.root.after(5000, self.stop_alarm)

    def on_close(self):
        self.running = False
        AudioPlayer.stop()
        GPIO.cleanup()
        self.save_config()
        self.root.destroy()


def main():
    AudioPlayer.setup()
    root = tk.Tk()
    app = AlarmClockApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
