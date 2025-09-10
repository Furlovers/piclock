import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
from datetime import datetime
from pathlib import Path
import RPi.GPIO as GPIO

CONFIG_FILE = "config.json"

# Configuração de estilo para tela de 7 polegadas
SCREEN_CONFIG = {
    "font_time": ("Helvetica", 64, "bold"),
    "font_date": ("Helvetica", 16),
    "font_status": ("Helvetica", 18),
    "font_next_alarm": ("Helvetica", 12),
    "font_buttons": ("Helvetica", 12, "bold"),
    "button_padx": 10,
    "button_pady": 6,
    "main_pady": 10
}

class AudioPlayer:
    buzzer_pin = 23
    _is_playing = False

    @staticmethod
    def setup():
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(AudioPlayer.buzzer_pin, GPIO.OUT)
        GPIO.output(AudioPlayer.buzzer_pin, GPIO.LOW)

    @staticmethod
    def play(volume=70):
        if AudioPlayer._is_playing:
            return
        AudioPlayer._is_playing = True
        threading.Thread(target=AudioPlayer._buzz, daemon=True).start()

    @staticmethod
    def stop():
        AudioPlayer._is_playing = False
        GPIO.output(AudioPlayer.buzzer_pin, GPIO.LOW)

    @staticmethod
    def is_playing():
        return AudioPlayer._is_playing

    @staticmethod
    def _buzz():
        while AudioPlayer._is_playing:
            GPIO.output(AudioPlayer.buzzer_pin, GPIO.HIGH)
            time.sleep(0.2)
            GPIO.output(AudioPlayer.buzzer_pin, GPIO.LOW)
            time.sleep(0.2)


class AlarmDialog:
    def __init__(self, parent, alarm=None, index=None):
        self.parent = parent
        self.alarm = alarm or {}
        self.index = index
        self.is_edit = alarm is not None

        # Criar janela de diálogo
        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("Adicionar Alarme" if not self.is_edit else "Editar Alarme")
        self.dialog.geometry("360x480")  # Tamanho reduzido para tela menor
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#0a0a0a")
        self.dialog.grab_set()

        # Centralizar na tela
        self.dialog.transient(parent.root)
        self.dialog.update_idletasks()
        x = parent.root.winfo_x() + (parent.root.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.root.winfo_y() + (parent.root.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")

        # Configuração de estilo
        self.colors = parent.colors

        self.create_widgets()
        self.load_alarm_data()

    def create_widgets(self):
        # Frame principal
        main_frame = tk.Frame(self.dialog, bg=self.colors["background"], padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)

        # Título
        title = tk.Label(
            main_frame,
            text="Adicionar Alarme" if not self.is_edit else "Editar Alarme",
            font=("Helvetica", 16, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        title.pack(pady=(0, 15))

        # Descrição do alarme
        tk.Label(
            main_frame,
            text="Descrição:",
            font=("Helvetica", 11),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(5, 0))

        self.label_entry = tk.Entry(
            main_frame,
            font=("Helvetica", 12),
            bg="#2d3436",
            fg=self.colors["text"],
            insertbackground="white",
        )
        self.label_entry.pack(fill="x", pady=(5, 10))

        # Hora do alarme
        time_frame = tk.Frame(main_frame, bg=self.colors["background"])
        time_frame.pack(fill="x", pady=8)

        tk.Label(
            time_frame,
            text="Horário:",
            font=("Helvetica", 11),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w")

        time_input_frame = tk.Frame(time_frame, bg=self.colors["background"])
        time_input_frame.pack(fill="x", pady=(5, 0))

        # Hora
        self.hour_var = tk.StringVar(value="07")
        hour_spinbox = tk.Spinbox(
            time_input_frame,
            from_=0,
            to=23,
            format="%02.0f",
            textvariable=self.hour_var,
            width=4,
            font=("Helvetica", 12),
            bg="#2d3436",
            fg=self.colors["text"],
            justify="center",
        )
        hour_spinbox.pack(side="left", padx=(0, 5))

        tk.Label(
            time_input_frame,
            text=":",
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(side="left")

        # Minutos
        self.minute_var = tk.StringVar(value="00")
        minute_spinbox = tk.Spinbox(
            time_input_frame,
            from_=0,
            to=59,
            format="%02.0f",
            textvariable=self.minute_var,
            width=4,
            font=("Helvetica", 12),
            bg="#2d3436",
            fg=self.colors["text"],
            justify="center",
        )
        minute_spinbox.pack(side="left", padx=(5, 0))

        # Dias da semana
        tk.Label(
            main_frame,
            text="Repetir:",
            font=("Helvetica", 11),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(12, 5))

        days_frame = tk.Frame(main_frame, bg=self.colors["background"])
        days_frame.pack(fill="x", pady=(5, 10))

        self.days_vars = []
        days = ["S", "T", "Q", "Q", "S", "S", "D"]  # Abreviado para caber na tela

        for i, day in enumerate(days):
            var = tk.BooleanVar(value=True if i < 5 else False)  # Seg-Sex marcados por padrão
            self.days_vars.append(var)

            cb = tk.Checkbutton(
                days_frame,
                text=day,
                variable=var,
                font=("Helvetica", 10, "bold"),
                fg=self.colors["text"],
                bg=self.colors["background"],
                selectcolor=self.colors["primary"],
                activebackground=self.colors["background"],
                activeforeground=self.colors["text"],
                width=2
            )
            cb.grid(row=0, column=i, padx=2)

        # Volume
        tk.Label(
            main_frame,
            text="Volume:",
            font=("Helvetica", 11),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(12, 5))

        self.volume_var = tk.IntVar(value=70)
        volume_scale = tk.Scale(
            main_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.volume_var,
            bg=self.colors["background"],
            fg=self.colors["text"],
            troughcolor="#2d3436",
            highlightbackground=self.colors["background"],
            sliderrelief="flat",
            length=250
        )
        volume_scale.pack(fill="x", pady=(5, 10))

        # Ativo/Inativo
        self.enabled_var = tk.BooleanVar(value=True)
        enabled_cb = tk.Checkbutton(
            main_frame,
            text="Ativo",
            variable=self.enabled_var,
            font=("Helvetica", 11),
            fg=self.colors["text"],
            bg=self.colors["background"],
            selectcolor=self.colors["primary"],
            activebackground=self.colors["background"],
            activeforeground=self.colors["text"],
        )
        enabled_cb.pack(anchor="w", pady=(10, 15))

        # Botões
        button_frame = tk.Frame(main_frame, bg=self.colors["background"])
        button_frame.pack(fill="x", pady=(10, 0))

        if self.is_edit:
            delete_btn = tk.Button(
                button_frame,
                text="Excluir",
                font=("Helvetica", 11, "bold"),
                bg=self.colors["danger"],
                fg="white",
                relief="flat",
                padx=12,
                pady=6,
                command=self.delete_alarm,
                cursor="hand2",
            )
            delete_btn.pack(side="left", padx=(0, 8))

        cancel_btn = tk.Button(
            button_frame,
            text="Cancelar",
            font=("Helvetica", 11, "bold"),
            bg="#636e72",
            fg="white",
            relief="flat",
            padx=12,
            pady=6,
            command=self.dialog.destroy,
            cursor="hand2",
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        save_btn = tk.Button(
            button_frame,
            text="Salvar",
            font=("Helvetica", 11, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=12,
            pady=6,
            command=self.save_alarm,
            cursor="hand2",
        )
        save_btn.pack(side="right", padx=(0, 8))

    def load_alarm_data(self):
        if self.alarm:
            self.label_entry.insert(0, self.alarm.get("label", ""))
            if "time" in self.alarm:
                time_parts = self.alarm["time"].split(":")
                self.hour_var.set(time_parts[0])
                self.minute_var.set(time_parts[1])
            if "days" in self.alarm:
                for i, day in enumerate(self.alarm["days"]):
                    if i < len(self.days_vars):
                        self.days_vars[i].set(day)
            self.volume_var.set(self.alarm.get("volume", 70))
            self.enabled_var.set(self.alarm.get("enabled", True))

    def save_alarm(self):
        label = self.label_entry.get().strip()
        if not label:
            messagebox.showerror("Erro", "Por favor, insira uma descrição para o alarme.")
            return

        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira um horário válido.")
            return

        days = []
        for i, var in enumerate(self.days_vars):
            if var.get():
                days.append(i)

        if not days:
            messagebox.showerror("Erro", "Selecione pelo menos um dia da semana.")
            return

        alarm_data = {
            "label": label,
            "time": f"{hour:02d}:{minute:02d}",
            "days": days,
            "volume": self.volume_var.get(),
            "enabled": self.enabled_var.get(),
        }

        if self.is_edit:
            self.parent.update_alarm(self.index, alarm_data)
        else:
            self.parent.add_alarm(alarm_data)

        self.dialog.destroy()

    def delete_alarm(self):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este alarme?"):
            self.parent.delete_alarm(self.index)
            self.dialog.destroy()


class AlarmClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Relógio Inteligente")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#0a0a0a")

        self.colors = {
            "background": "#0a0a0a",
            "primary": "#2e86de",
            "secondary": "#a29bfe",
            "accent": "#ff6b6b",
            "text": "#ffffff",
            "text_secondary": "#b2bec3",
            "success": "#1dd1a1",
            "warning": "#feca57",
            "danger": "#ff6b6b",
        }

        # Inicializar player de áudio
        AudioPlayer.setup()

        # Simular botões GPIO (substitua pela sua implementação real)
        self.buttons = type('Obj', (object,), {'start': lambda: None, 'cleanup': lambda: None})()
        
        self.alarms = []
        self.load_config()

        # Layout principal otimizado para tela pequena
        self.main_frame = tk.Frame(root, bg=self.colors["background"])
        self.main_frame.pack(expand=True, fill="both", pady=SCREEN_CONFIG["main_pady"])

        # Data atual (menor)
        self.date_label = tk.Label(
            self.main_frame,
            text="",
            font=SCREEN_CONFIG["font_date"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.date_label.pack(pady=(20, 5))

        # Hora (tamanho reduzido)
        self.time_label = tk.Label(
            self.main_frame,
            text="",
            font=SCREEN_CONFIG["font_time"],
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        self.time_label.pack(expand=True, pady=10)

        # Status do alarme
        self.status_label = tk.Label(
            self.main_frame,
            text="Nenhum alarme ativo",
            font=SCREEN_CONFIG["font_status"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.status_label.pack(pady=8)

        # Próximo alarme (menor)
        self.next_alarm_label = tk.Label(
            self.main_frame,
            text="",
            font=SCREEN_CONFIG["font_next_alarm"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.next_alarm_label.pack(pady=5)
        self.update_next_alarm()

        # Frame dos botões (mais compacto)
        self.button_frame = tk.Frame(root, bg=self.colors["background"])
        self.button_frame.pack(side="bottom", fill="x", pady=10)

        # Botão para adicionar alarme (menor)
        self.add_alarm_btn = tk.Button(
            self.button_frame,
            text="+",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            width=2,
            height=1,
            command=self.show_alarm_dialog,
            cursor="hand2",
        )
        self.add_alarm_btn.pack(side="left", padx=SCREEN_CONFIG["button_padx"], pady=SCREEN_CONFIG["button_pady"])

        # Botão para testar alarme (menor)
        self.test_alarm_btn = tk.Button(
            self.button_frame,
            text="Testar",
            font=SCREEN_CONFIG["font_buttons"],
            bg=self.colors["accent"],
            fg="white",
            relief="flat",
            padx=15,
            pady=SCREEN_CONFIG["button_pady"],
            command=self.test_alarm,
            cursor="hand2",
        )
        self.test_alarm_btn.pack(side="left", padx=SCREEN_CONFIG["button_padx"], pady=SCREEN_CONFIG["button_pady"])

        # Botão para parar alarme (menor)
        self.stop_alarm_btn = tk.Button(
            self.button_frame,
            text="Parar",
            font=SCREEN_CONFIG["font_buttons"],
            bg=self.colors["danger"],
            fg="white",
            relief="flat",
            padx=15,
            pady=SCREEN_CONFIG["button_pady"],
            command=self.stop_alarm,
            cursor="hand2",
        )
        self.stop_alarm_btn.pack(side="left", padx=SCREEN_CONFIG["button_padx"], pady=SCREEN_CONFIG["button_pady"])

        # Indicador de status (menor)
        self.status_indicator = tk.Canvas(
            self.button_frame, width=24, height=24, bg=self.colors["background"], highlightthickness=0
        )
        self.status_indicator.pack(side="right", padx=15)
        self.indicator = self.status_indicator.create_oval(3, 3, 21, 21, fill=self.colors["success"], outline="")

        # Thread de checagem de alarmes
        self.running = True
        self.alarm_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.alarm_thread.start()

        self.update_clock()

    def show_alarm_dialog(self, alarm=None, index=None):
        AlarmDialog(self, alarm, index)

    def add_alarm(self, alarm_data):
        self.alarms.append(alarm_data)
        self.save_config()
        self.update_next_alarm()

    def update_alarm(self, index, alarm_data):
        if 0 <= index < len(self.alarms):
            self.alarms[index] = alarm_data
            self.save_config()
            self.update_next_alarm()

    def delete_alarm(self, index):
        if 0 <= index < len(self.alarms):
            self.alarms.pop(index)
            self.save_config()
            self.update_next_alarm()

    def update_next_alarm(self):
        next_alarm = self.get_next_alarm()
        if next_alarm:
            days_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            days_str = ", ".join([days_map[d] for d in next_alarm["days"]])
            # Texto mais curto para caber na tela
            self.next_alarm_label.config(text=f"Próx: {next_alarm['time']} - {next_alarm['label'][:15]}{'...' if len(next_alarm['label']) > 15 else ''}")
        else:
            self.next_alarm_label.config(text="Sem alarmes")

    def get_next_alarm(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.weekday()

        enabled_alarms = [a for a in self.alarms if a.get("enabled", False)]
        if not enabled_alarms:
            return None

        enabled_alarms.sort(key=lambda x: x["time"])

        for alarm in enabled_alarms:
            if alarm["time"] > current_time and current_weekday in alarm.get("days", []):
                return alarm

        for i in range(1, 8):
            next_day = (current_weekday + i) % 7
            for alarm in enabled_alarms:
                if next_day in alarm.get("days", []):
                    return alarm

        return None

    def load_config(self):
        try:
            if not Path(CONFIG_FILE).exists():
                raise FileNotFoundError

            with open(CONFIG_FILE) as f:
                cfg = json.load(f)

        except (FileNotFoundError, json.JSONDecodeError):
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
        date_str = now.strftime("%d/%m/%Y - %A")  # Formato mais compacto

        # Efeito de piscar os dois pontos
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
                    weekday = now.weekday()
                    if weekday in alarm.get("days", []):
                        self.trigger_alarm(alarm)
            time.sleep(30)

    def trigger_alarm(self, alarm):
        volume = alarm.get("volume", 70)
        AudioPlayer.play(volume)
        self.status_label.config(text=f"ALARME: {alarm.get('label', '')}", fg=self.colors["danger"])
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["danger"])

    def stop_alarm(self):
        AudioPlayer.stop()
        self.status_label.config(text="Nenhum alarme ativo", fg=self.colors["text_secondary"])
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["success"])

    def test_alarm(self):
        AudioPlayer.play(70)
        self.status_label.config(text="🔔 Testando alarme", fg=self.colors["warning"])
        self.status_indicator.itemconfig(self.indicator, fill=self.colors["warning"])
        self.root.after(5000, self.stop_alarm)

    def handle_gpio(self, button):
        if button == "stop":
            self.stop_alarm()
        elif button == "snooze":
            self.stop_alarm()
            self.root.after(self.snooze_minutes * 60 * 1000, lambda: AudioPlayer.play(70))

    def on_close(self):
        self.running = False
        if hasattr(self.buttons, 'cleanup'):
            self.buttons.cleanup()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = AlarmClockApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    
    # Configurar para fechar com a tecla ESC
    root.bind('<Escape>', lambda e: app.on_close())
    
    root.mainloop()


if __name__ == "__main__":
    main()