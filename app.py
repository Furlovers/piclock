import tkinter as tk
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import RPi.GPIO as GPIO

from audio import AudioPlayer
from brightness import Backlight
from rtc_sync import RTC
from gpio_buttons import GpioButtons

CONFIG_FILE = "config.json"

class AlarmClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Relógio Inteligente")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0a0a0a")
        
        # Configuração de estilo
        self.colors = {
            "background": "#0a0a0a",
            "primary": "#2e86de",
            "secondary": "#a29bfe",
            "accent": "#ff6b6b",
            "text": "#ffffff",
            "text_secondary": "#b2bec3",
            "success": "#1dd1a1",
            "warning": "#feca57",
            "danger": "#ff6b6b"
        }

        # Inicializações
        self.audio = AudioPlayer()
        self.buttons = GpioButtons(callback=self.handle_gpio)
        self.buttons.start()

        self.alarms = []
        self.load_config()

        # Frame principal para relógio e status
        self.main_frame = tk.Frame(root, bg=self.colors["background"])
        self.main_frame.pack(expand=True, fill="both")

        # Data atual
        self.date_label = tk.Label(
            self.main_frame, 
            text="", 
            font=("Helvetica", 20), 
            fg=self.colors["text_secondary"], 
            bg=self.colors["background"]
        )
        self.date_label.pack(pady=(40, 0))

        # Label do relógio
        self.time_label = tk.Label(
            self.main_frame, 
            text="", 
            font=("Helvetica", 96, "bold"), 
            fg=self.colors["primary"], 
            bg=self.colors["background"]
        )
        self.time_label.pack(expand=True, pady=20)

        # Label do status do alarme
        self.status_label = tk.Label(
            self.main_frame, 
            text="Nenhum alarme ativo", 
            font=("Helvetica", 24), 
            fg=self.colors["text_secondary"], 
            bg=self.colors["background"]
        )
        self.status_label.pack(pady=10)

        # Frame dos botões na parte inferior
        self.button_frame = tk.Frame(root, bg=self.colors["background"])
        self.button_frame.pack(side="bottom", fill="x", pady=20)

        # Botão para disparar alarme manualmente
        self.test_alarm_btn = tk.Button(
            self.button_frame,
            text="Testar Alarme",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["accent"],
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            command=self.test_alarm,
            cursor="hand2"
        )
        self.test_alarm_btn.pack(side="left", padx=20, pady=5)

        # Botão para parar alarme
        self.stop_alarm_btn = tk.Button(
            self.button_frame,
            text="Parar Alarme",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            padx=20,
            pady=10,
            command=self.stop_alarm,
            cursor="hand2"
        )
        self.stop_alarm_btn.pack(side="left", padx=20, pady=5)

        # Indicador de status (círculo)
        self.status_indicator = tk.Canvas(
            self.button_frame, 
            width=30, 
            height=30, 
            bg=self.colors["background"],
            highlightthickness=0
        )
        self.status_indicator.pack(side="right", padx=20)
        self.indicator = self.status_indicator.create_oval(
            5, 5, 25, 25, 
            fill=self.colors["success"], 
            outline=""
        )

        # Thread de checagem de alarmes
        self.running = True
        self.alarm_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.alarm_thread.start()

        self.update_clock()

    def load_config(self):
        try:
            if not Path(CONFIG_FILE).exists():
                raise FileNotFoundError

            with open(CONFIG_FILE) as f:
                cfg = json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
            # cria config padrão
            cfg = {
                "alarms": [],
                "snooze_minutes": 10,
                "brightness": 180,
                "auto_dim": {"enabled": False, "night": 40, "start": "22:30", "end": "06:30"},
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(cfg, f, indent=2)

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
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%A, %d %B %Y").title()
        
        # Formatação com separador piscante
        if int(now.second) % 2 == 0:
            time_str = time_str.replace(":", " ")
        else:
            time_str = time_str.replace(" ", ":")
            
        self.time_label.config(text=time_str)
        self.date_label.config(text=date_str)
        self.root.after(1000, self.update_clock)

    def check_alarms(self):
        while self.running:
            now = datetime.now()
            for alarm in self.alarms:
                if not alarm.get("enabled", False):
                    continue

                if now.strftime("%H:%M") == alarm["time"]:
                    weekday = now.weekday()  # 0 = seg
                    if weekday in alarm.get("days", []):
                        self.trigger_alarm(alarm)

            time.sleep(30)

    def trigger_alarm(self, alarm):
        volume = alarm.get("volume", 70)
        AudioPlayer.set_volume(volume)
        self.audio.play(loop=True)
        self.status_label.config(
            text=f"ALARME: {alarm.get('label', '')}", 
            fg=self.colors["danger"]
        )
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["danger"])
        self.flash_background()

    def flash_background(self):
        if self.audio.is_playing():
            current_color = self.main_frame.cget("bg")
            new_color = self.colors["danger"] if current_color == self.colors["background"] else self.colors["background"]
            self.main_frame.configure(bg=new_color)
            self.time_label.configure(bg=new_color)
            self.date_label.configure(bg=new_color)
            self.status_label.configure(bg=new_color)
            self.root.after(500, self.flash_background)

    def handle_gpio(self, event):
        if event == "snooze":
            self.snooze_alarm()
        elif event == "stop":
            self.stop_alarm()

    def snooze_alarm(self):
        self.audio.stop()
        self.status_label.config(
            text=f"Soneca ativada ({self.snooze_minutes} min)", 
            fg=self.colors["warning"]
        )
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["warning"])
        self.reset_background()
        threading.Thread(target=self._snooze_wait, daemon=True).start()

    def _snooze_wait(self):
        time.sleep(self.snooze_minutes * 60)
        self.status_label.config(text="Soneca terminou", fg=self.colors["danger"])
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["danger"])
        if self.alarms:
            self.trigger_alarm(self.alarms[0])

    def stop_alarm(self):
        self.audio.stop()
        self.status_label.config(
            text="Alarme parado", 
            fg=self.colors["success"]
        )
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["success"])
        self.reset_background()
        # Volta ao normal após 3 segundos
        self.root.after(3000, lambda: self.status_label.config(
            text="Nenhum alarme ativo", 
            fg=self.colors["text_secondary"]
        ))
        self.root.after(3000, lambda: self.status_indicator.itemconfig(
            self.indicator, fill=self.colors["success"]
        ))

    def reset_background(self):
        self.main_frame.configure(bg=self.colors["background"])
        self.time_label.configure(bg=self.colors["background"])
        self.date_label.configure(bg=self.colors["background"])
        self.status_label.configure(bg=self.colors["background"])

    def test_alarm(self):
        if self.alarms:
            self.trigger_alarm(self.alarms[0])
        else:
            test_alarm = {
                "time": datetime.now().strftime("%H:%M"),
                "days": [0,1,2,3,4,5,6],
                "label": "Alarme Manual",
                "volume": 70
            }
            self.trigger_alarm(test_alarm)

    def on_close(self):
        self.running = False
        self.buttons.stop()
        self.audio.stop()
        self.save_config()
        GPIO.cleanup()  # limpa todos os pinos GPIO
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmClockApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()