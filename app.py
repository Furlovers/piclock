import tkinter as tk
from tkinter import ttk, messagebox
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

class AlarmDialog:
    def __init__(self, parent, alarm=None, index=None):
        self.parent = parent
        self.alarm = alarm or {}
        self.index = index
        self.is_edit = alarm is not None
        
        # Criar janela de diálogo
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Adicionar Alarme" if not self.is_edit else "Editar Alarme")
        self.dialog.geometry("400x500")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#0a0a0a")
        self.dialog.grab_set()  # Tornar modal
        
        # Centralizar na tela
        self.dialog.transient(parent)
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
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
        
        self.create_widgets()
        self.load_alarm_data()
    
    def create_widgets(self):
        # Frame principal
        main_frame = tk.Frame(self.dialog, bg=self.colors["background"], padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Título
        title = tk.Label(
            main_frame, 
            text="Adicionar Alarme" if not self.is_edit else "Editar Alarme",
            font=("Helvetica", 18, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["background"]
        )
        title.pack(pady=(0, 20))
        
        # Label para o alarme
        tk.Label(
            main_frame,
            text="Descrição:",
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(anchor="w", pady=(5, 0))
        
        self.label_entry = tk.Entry(
            main_frame,
            font=("Helvetica", 14),
            bg="#2d3436",
            fg=self.colors["text"],
            insertbackground="white"
        )
        self.label_entry.pack(fill="x", pady=(5, 10))
        
        # Hora do alarme
        time_frame = tk.Frame(main_frame, bg=self.colors["background"])
        time_frame.pack(fill="x", pady=10)
        
        tk.Label(
            time_frame,
            text="Horário:",
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(anchor="w")
        
        # Frame para hora e minutos
        time_input_frame = tk.Frame(time_frame, bg=self.colors["background"])
        time_input_frame.pack(fill="x", pady=(5, 0))
        
        # Hora
        self.hour_var = tk.StringVar(value="00")
        hour_spinbox = tk.Spinbox(
            time_input_frame,
            from_=0, to=23,
            format="%02.0f",
            textvariable=self.hour_var,
            width=5,
            font=("Helvetica", 14),
            bg="#2d3436",
            fg=self.colors["text"],
            buttonbackground=self.colors["primary"],
            justify="center"
        )
        hour_spinbox.pack(side="left", padx=(0, 5))
        
        tk.Label(
            time_input_frame,
            text=":",
            font=("Helvetica", 14),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(side="left")
        
        # Minutos
        self.minute_var = tk.StringVar(value="00")
        minute_spinbox = tk.Spinbox(
            time_input_frame,
            from_=0, to=59,
            format="%02.0f",
            textvariable=self.minute_var,
            width=5,
            font=("Helvetica", 14),
            bg="#2d3436",
            fg=self.colors["text"],
            buttonbackground=self.colors["primary"],
            justify="center"
        )
        minute_spinbox.pack(side="left", padx=(5, 0))
        
        # Dias da semana
        tk.Label(
            main_frame,
            text="Repetir:",
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(anchor="w", pady=(15, 5))
        
        days_frame = tk.Frame(main_frame, bg=self.colors["background"])
        days_frame.pack(fill="x", pady=(5, 10))
        
        self.days_vars = []
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        for i, day in enumerate(days):
            var = tk.BooleanVar()
            self.days_vars.append(var)
            
            cb = tk.Checkbutton(
                days_frame,
                text=day,
                variable=var,
                font=("Helvetica", 10),
                fg=self.colors["text"],
                bg=self.colors["background"],
                selectcolor=self.colors["primary"],
                activebackground=self.colors["background"],
                activeforeground=self.colors["text"]
            )
            cb.grid(row=0, column=i, padx=2)
        
        # Volume
        tk.Label(
            main_frame,
            text="Volume:",
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"]
        ).pack(anchor="w", pady=(15, 5))
        
        self.volume_var = tk.IntVar(value=70)
        volume_scale = tk.Scale(
            main_frame,
            from_=0, to=100,
            orient="horizontal",
            variable=self.volume_var,
            bg=self.colors["background"],
            fg=self.colors["text"],
            troughcolor="#2d3436",
            highlightbackground=self.colors["background"],
            sliderrelief="flat",
            length=300
        )
        volume_scale.pack(fill="x", pady=(5, 10))
        
        # Ativo/Inativo
        self.enabled_var = tk.BooleanVar(value=True)
        enabled_cb = tk.Checkbutton(
            main_frame,
            text="Ativo",
            variable=self.enabled_var,
            font=("Helvetica", 12),
            fg=self.colors["text"],
            bg=self.colors["background"],
            selectcolor=self.colors["primary"],
            activebackground=self.colors["background"],
            activeforeground=self.colors["text"]
        )
        enabled_cb.pack(anchor="w", pady=(10, 20))
        
        # Botões
        button_frame = tk.Frame(main_frame, bg=self.colors["background"])
        button_frame.pack(fill="x", pady=(10, 0))
        
        if self.is_edit:
            delete_btn = tk.Button(
                button_frame,
                text="Excluir",
                font=("Helvetica", 12, "bold"),
                bg=self.colors["danger"],
                fg="white",
                relief="flat",
                padx=15,
                pady=8,
                command=self.delete_alarm,
                cursor="hand2"
            )
            delete_btn.pack(side="left", padx=(0, 10))
        
        cancel_btn = tk.Button(
            button_frame,
            text="Cancelar",
            font=("Helvetica", 12, "bold"),
            bg="#636e72",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            command=self.dialog.destroy,
            cursor="hand2"
        )
        cancel_btn.pack(side="right", padx=(10, 0))
        
        save_btn = tk.Button(
            button_frame,
            text="Salvar",
            font=("Helvetica", 12, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            command=self.save_alarm,
            cursor="hand2"
        )
        save_btn.pack(side="right")
    
    def load_alarm_data(self):
        if self.alarm:
            # Preencher campos com dados existentes
            self.label_entry.insert(0, self.alarm.get("label", ""))
            
            # Extrair hora e minuto
            if "time" in self.alarm:
                time_parts = self.alarm["time"].split(":")
                self.hour_var.set(time_parts[0])
                self.minute_var.set(time_parts[1])
            
            # Marcar dias da semana
            if "days" in self.alarm:
                for i, day in enumerate(self.alarm["days"]):
                    if i < len(self.days_vars):
                        self.days_vars[i].set(day)
            
            # Configurar volume
            self.volume_var.set(self.alarm.get("volume", 70))
            
            # Configurar estado ativo/inativo
            self.enabled_var.set(self.alarm.get("enabled", True))
    
    def save_alarm(self):
        # Validar dados
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
        
        # Coletar dias selecionados
        days = []
        for i, var in enumerate(self.days_vars):
            if var.get():
                days.append(i)
        
        if not days:
            messagebox.showerror("Erro", "Selecione pelo menos um dia da semana.")
            return
        
        # Criar objeto de alarme
        alarm_data = {
            "label": label,
            "time": f"{hour:02d}:{minute:02d}",
            "days": days,
            "volume": self.volume_var.get(),
            "enabled": self.enabled_var.get()
        }
        
        # Salvar ou atualizar alarme
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
        
        # Próximo alarme
        self.next_alarm_label = tk.Label(
            self.main_frame, 
            text="", 
            font=("Helvetica", 16), 
            fg=self.colors["text_secondary"], 
            bg=self.colors["background"]
        )
        self.next_alarm_label.pack(pady=5)
        self.update_next_alarm()

        # Frame dos botões na parte inferior
        self.button_frame = tk.Frame(root, bg=self.colors["background"])
        self.button_frame.pack(side="bottom", fill="x", pady=20)

        # Botão para adicionar alarme
        self.add_alarm_btn = tk.Button(
            self.button_frame,
            text="+",
            font=("Helvetica", 20, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            width=3,
            height=1,
            command=self.show_alarm_dialog,
            cursor="hand2"
        )
        self.add_alarm_btn.pack(side="left", padx=20, pady=5)

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
            self.next_alarm_label.config(
                text=f"Próximo: {next_alarm['time']} ({days_str}) - {next_alarm['label']}"
            )
        else:
            self.next_alarm_label.config(text="Nenhum alarme programado")
    
    def get_next_alarm(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_weekday = now.weekday()
        
        enabled_alarms = [a for a in self.alarms if a.get("enabled", False)]
        if not enabled_alarms:
            return None
        
        # Ordenar alarmes por horário
        enabled_alarms.sort(key=lambda x: x["time"])
        
        # Encontrar o próximo alarme de hoje
        for alarm in enabled_alarms:
            if alarm["time"] > current_time and current_weekday in alarm.get("days", []):
                return alarm
        
        # Se não encontrou hoje, procurar nos próximos dias
        for i in range(1, 8):  # Próximos 7 dias
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
            self.next_alarm_label.configure(bg=new_color)
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
        self.next_alarm_label.configure(bg=self.colors["background"])

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