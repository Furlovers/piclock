import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
import random
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
    "font_temp": ("Helvetica", 14),
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


class WeatherService:
    @staticmethod
    def get_weather():
        # Simulação de dados meteorológicos
        # Em uma implementação real, você conectaria a uma API de previsão do tempo
        temperatures = [22, 23, 24, 25, 26, 27, 28, 29, 30]
        conditions = ["sunny", "partly_cloudy", "cloudy", "rainy"]
        weather_icons = {
            "sunny": "☀️",
            "partly_cloudy": "⛅",
            "cloudy": "☁️",
            "rainy": "🌧️"
        }
        
        temp = random.choice(temperatures)
        condition = random.choice(conditions)
        
        return {
            "temperature": temp,
            "condition": condition,
            "icon": weather_icons[condition]
        }


class AlarmDialog:
    def __init__(self, parent, alarm=None, index=None):
        self.parent = parent
        self.alarm = alarm or {}
        self.index = index
        self.is_edit = alarm is not None

        # Criar janela de diálogo em full screen
        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("Adicionar Alarme" if not self.is_edit else "Editar Alarme")
        
        # Obter dimensões da tela
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # Configurar para ocupar quase toda a tela, mas deixar uma pequena margem
        self.dialog.geometry(f"{screen_width}x{screen_height}+0+0")
        self.dialog.attributes('-fullscreen', True)
        self.dialog.configure(bg="#0a0a0a")
        self.dialog.grab_set()  # Tornar modal

        # Configuração de estilo
        self.colors = parent.colors
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.create_widgets()
        self.load_alarm_data()
        
        # Adicionar botão de voltar no canto superior esquerdo
        self.add_back_button()

    def add_back_button(self):
        back_btn = tk.Button(
            self.dialog,
            text="← Voltar",
            font=("Helvetica", 14, "bold"),
            bg=self.colors["secondary"],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            command=self.dialog.destroy,
            cursor="hand2",
        )
        back_btn.place(x=20, y=20)

    def create_widgets(self):
        # Frame principal centralizado
        main_frame = tk.Frame(
            self.dialog, 
            bg=self.colors["background"], 
            padx=30, 
            pady=30,
            width=self.screen_width * 0.8,
            height=self.screen_height * 0.8
        )
        main_frame.place(relx=0.5, rely=0.5, anchor="center")
        main_frame.pack_propagate(False)  # Impede que o frame redimensione seus filhos

        # Título
        title = tk.Label(
            main_frame,
            text="Adicionar Alarme" if not self.is_edit else "Editar Alarme",
            font=("Helvetica", 24, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        title.pack(pady=(0, 30))

        # Frame para formulário com scrollbar se necessário
        form_frame = tk.Frame(main_frame, bg=self.colors["background"])
        form_frame.pack(fill="both", expand=True)

        # Descrição do alarme
        tk.Label(
            form_frame,
            text="Descrição:",
            font=("Helvetica", 16),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(10, 5))

        self.label_entry = tk.Entry(
            form_frame,
            font=("Helvetica", 16),
            bg="#2d3436",
            fg=self.colors["text"],
            insertbackground="white",
        )
        self.label_entry.pack(fill="x", pady=(5, 15))

        # Hora do alarme
        time_frame = tk.Frame(form_frame, bg=self.colors["background"])
        time_frame.pack(fill="x", pady=15)

        tk.Label(
            time_frame,
            text="Horário:",
            font=("Helvetica", 16),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w")

        time_input_frame = tk.Frame(time_frame, bg=self.colors["background"])
        time_input_frame.pack(fill="x", pady=(10, 0))

        # Hora
        self.hour_var = tk.StringVar(value="07")
        hour_spinbox = tk.Spinbox(
            time_input_frame,
            from_=0,
            to=23,
            format="%02.0f",
            textvariable=self.hour_var,
            width=4,
            font=("Helvetica", 20),
            bg="#2d3436",
            fg=self.colors["text"],
            justify="center",
        )
        hour_spinbox.pack(side="left", padx=(0, 10))

        tk.Label(
            time_input_frame,
            text=":",
            font=("Helvetica", 20),
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
            font=("Helvetica", 20),
            bg="#2d3436",
            fg=self.colors["text"],
            justify="center",
        )
        minute_spinbox.pack(side="left", padx=(10, 0))

        # Dias da semana
        tk.Label(
            form_frame,
            text="Repetir:",
            font=("Helvetica", 16),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(20, 10))

        days_frame = tk.Frame(form_frame, bg=self.colors["background"])
        days_frame.pack(fill="x", pady=(10, 15))

        self.days_vars = []
        days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

        for i, day in enumerate(days):
            var = tk.BooleanVar(value=True if i < 5 else False)
            self.days_vars.append(var)

            cb = tk.Checkbutton(
                days_frame,
                text=day,
                variable=var,
                font=("Helvetica", 14, "bold"),
                fg=self.colors["text"],
                bg=self.colors["background"],
                selectcolor=self.colors["primary"],
                activebackground=self.colors["background"],
                activeforeground=self.colors["text"],
                width=6,
                height=2
            )
            cb.grid(row=0, column=i, padx=5)

        # Volume
        tk.Label(
            form_frame,
            text="Volume:",
            font=("Helvetica", 16),
            fg=self.colors["text"],
            bg=self.colors["background"],
        ).pack(anchor="w", pady=(20, 10))

        self.volume_var = tk.IntVar(value=70)
        volume_scale = tk.Scale(
            form_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.volume_var,
            bg=self.colors["background"],
            fg=self.colors["text"],
            troughcolor="#2d3436",
            highlightbackground=self.colors["background"],
            sliderrelief="flat",
            length=400,
            font=("Helvetica", 12),
            sliderlength=30
        )
        volume_scale.pack(fill="x", pady=(10, 20))

        # Ativo/Inativo
        self.enabled_var = tk.BooleanVar(value=True)
        enabled_cb = tk.Checkbutton(
            form_frame,
            text="Ativo",
            variable=self.enabled_var,
            font=("Helvetica", 16),
            fg=self.colors["text"],
            bg=self.colors["background"],
            selectcolor=self.colors["primary"],
            activebackground=self.colors["background"],
            activeforeground=self.colors["text"],
        )
        enabled_cb.pack(anchor="w", pady=(15, 20))

        # Botões na parte inferior
        button_frame = tk.Frame(form_frame, bg=self.colors["background"])
        button_frame.pack(fill="x", pady=(20, 0))

        if self.is_edit:
            delete_btn = tk.Button(
                button_frame,
                text="Excluir",
                font=("Helvetica", 16, "bold"),
                bg=self.colors["danger"],
                fg="white",
                relief="flat",
                padx=20,
                pady=12,
                command=self.delete_alarm,
                cursor="hand2",
            )
            delete_btn.pack(side="left", padx=(0, 15))

        cancel_btn = tk.Button(
            button_frame,
            text="Cancelar",
            font=("Helvetica", 16, "bold"),
            bg="#636e72",
            fg="white",
            relief="flat",
            padx=20,
            pady=12,
            command=self.dialog.destroy,
            cursor="hand2",
        )
        cancel_btn.pack(side="right", padx=(15, 0))

        save_btn = tk.Button(
            button_frame,
            text="Salvar",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["success"],
            fg="white",
            relief="flat",
            padx=20,
            pady=12,
            command=self.save_alarm,
            cursor="hand2",
        )
        save_btn.pack(side="right", padx=(0, 15))

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


class AlarmListDialog:
    def __init__(self, parent):
        self.parent = parent
        
        # Criar janela de diálogo em full screen
        self.dialog = tk.Toplevel(parent.root)
        self.dialog.title("Lista de Alarmes")
        
        # Obter dimensões da tela
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # Configurar para ocupar toda a tela
        self.dialog.geometry(f"{screen_width}x{screen_height}+0+0")
        self.dialog.attributes('-fullscreen', True)
        self.dialog.configure(bg="#0a0a0a")
        self.dialog.grab_set()

        # Configuração de estilo
        self.colors = parent.colors
        self.screen_width = screen_width
        self.screen_height = screen_height

        self.create_widgets()
        
        # Adicionar botão de voltar
        self.add_back_button()

    def add_back_button(self):
        back_btn = tk.Button(
            self.dialog,
            text="← Voltar",
            font=("Helvetica", 14, "bold"),
            bg=self.colors["secondary"],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            command=self.dialog.destroy,
            cursor="hand2",
        )
        back_btn.place(x=20, y=20)

    def create_widgets(self):
        # Título
        title = tk.Label(
            self.dialog,
            text="Lista de Alarmes",
            font=("Helvetica", 24, "bold"),
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        title.pack(pady=(60, 20))

        # Frame para a lista de alarmes
        list_frame = tk.Frame(self.dialog, bg=self.colors["background"])
        list_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # Cabeçalho
        header_frame = tk.Frame(list_frame, bg=self.colors["background"])
        header_frame.pack(fill="x", pady=(0, 10))
        
        headers = ["Hora", "Descrição", "Dias", "Status", "Ações"]
        for i, header in enumerate(headers):
            tk.Label(
                header_frame,
                text=header,
                font=("Helvetica", 14, "bold"),
                fg=self.colors["primary"],
                bg=self.colors["background"],
            ).grid(row=0, column=i, padx=5, sticky="w")

        # Canvas e Scrollbar para a lista
        canvas = tk.Canvas(list_frame, bg=self.colors["background"], highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["background"])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Preencher com a lista de alarmes
        self.populate_alarm_list(scrollable_frame)

    def populate_alarm_list(self, parent_frame):
        days_map = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        
        for i, alarm in enumerate(self.parent.alarms):
            row_frame = tk.Frame(parent_frame, bg=self.colors["background"])
            row_frame.pack(fill="x", pady=5)
            
            # Hora
            tk.Label(
                row_frame,
                text=alarm["time"],
                font=("Helvetica", 14),
                fg=self.colors["text"],
                bg=self.colors["background"],
                width=8
            ).grid(row=0, column=0, padx=5, sticky="w")
            
            # Descrição
            tk.Label(
                row_frame,
                text=alarm.get("label", "Alarme"),
                font=("Helvetica", 14),
                fg=self.colors["text"],
                bg=self.colors["background"],
                width=20
            ).grid(row=0, column=1, padx=5, sticky="w")
            
            # Dias
            days_str = ",".join([days_map[d] for d in alarm.get("days", [])])
            tk.Label(
                row_frame,
                text=days_str,
                font=("Helvetica", 12),
                fg=self.colors["text_secondary"],
                bg=self.colors["background"],
                width=15
            ).grid(row=0, column=2, padx=5, sticky="w")
            
            # Status
            status_text = "Ativo" if alarm.get("enabled", False) else "Inativo"
            status_color = self.colors["success"] if alarm.get("enabled", False) else self.colors["danger"]
            tk.Label(
                row_frame,
                text=status_text,
                font=("Helvetica", 12),
                fg=status_color,
                bg=self.colors["background"],
                width=8
            ).grid(row=0, column=3, padx=5, sticky="w")
            
            # Ações
            action_frame = tk.Frame(row_frame, bg=self.colors["background"])
            action_frame.grid(row=0, column=4, padx=5, sticky="w")
            
            # Botão editar
            edit_btn = tk.Button(
                action_frame,
                text="✏️",
                font=("Helvetica", 12),
                bg=self.colors["primary"],
                fg="white",
                relief="flat",
                command=lambda idx=i: self.edit_alarm(idx),
                cursor="hand2",
            )
            edit_btn.pack(side="left", padx=2)
            
            # Botão toggle status
            toggle_text = "⏸️" if alarm.get("enabled", False) else "▶️"
            toggle_btn = tk.Button(
                action_frame,
                text=toggle_text,
                font=("Helvetica", 12),
                bg=self.colors["warning"],
                fg="white",
                relief="flat",
                command=lambda idx=i: self.toggle_alarm(idx),
                cursor="hand2",
            )
            toggle_btn.pack(side="left", padx=2)
            
            # Botão excluir
            delete_btn = tk.Button(
                action_frame,
                text="🗑️",
                font=("Helvetica", 12),
                bg=self.colors["danger"],
                fg="white",
                relief="flat",
                command=lambda idx=i: self.delete_alarm(idx),
                cursor="hand2",
            )
            delete_btn.pack(side="left", padx=2)

    def edit_alarm(self, index):
        self.dialog.destroy()
        self.parent.show_alarm_dialog(self.parent.alarms[index], index)

    def toggle_alarm(self, index):
        self.parent.alarms[index]["enabled"] = not self.parent.alarms[index]["enabled"]
        self.parent.save_config()
        self.dialog.destroy()
        AlarmListDialog(self.parent)  # Recria a janela para atualizar

    def delete_alarm(self, index):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja excluir este alarme?"):
            self.parent.delete_alarm(index)
            self.dialog.destroy()
            AlarmListDialog(self.parent)  # Recria a janela para atualizar


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

        # Inicializar dados meteorológicos
        self.weather_data = WeatherService.get_weather()
        
        # Layout principal otimizado para tela pequena
        self.main_frame = tk.Frame(root, bg=self.colors["background"])
        self.main_frame.pack(expand=True, fill="both", pady=SCREEN_CONFIG["main_pady"])

        # Barra superior com informações meteorológicas
        self.create_weather_bar()

        # Data atual
        self.date_label = tk.Label(
            self.main_frame,
            text="",
            font=SCREEN_CONFIG["font_date"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.date_label.pack(pady=(10, 5))

        # Hora
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

        # Próximo alarme
        self.next_alarm_label = tk.Label(
            self.main_frame,
            text="",
            font=SCREEN_CONFIG["font_next_alarm"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.next_alarm_label.pack(pady=5)
        self.update_next_alarm()

        # Frame dos botões
        self.button_frame = tk.Frame(root, bg=self.colors["background"])
        self.button_frame.pack(side="bottom", fill="x", pady=10)

        # Botão para lista de alarmes
        self.list_alarm_btn = tk.Button(
            self.button_frame,
            text="📋",
            font=("Helvetica", 16, "bold"),
            bg=self.colors["secondary"],
            fg="white",
            relief="flat",
            width=2,
            height=1,
            command=self.show_alarm_list,
            cursor="hand2",
        )
        self.list_alarm_btn.pack(side="left", padx=SCREEN_CONFIG["button_padx"], pady=SCREEN_CONFIG["button_pady"])

        # Botão para adicionar alarme
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

        # Botão para testar alarme
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

        # Botão para parar alarme
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

        # Indicador de status
        self.status_indicator = tk.Canvas(
            self.button_frame, width=24, height=24, bg=self.colors["background"], highlightthickness=0
        )
        self.status_indicator.pack(side="right", padx=15)
        self.indicator = self.status_indicator.create_oval(3, 3, 21, 21, fill=self.colors["success"], outline="")

        # Thread de checagem de alarmes
        self.running = True
        self.alarm_thread = threading.Thread(target=self.check_alarms, daemon=True)
        self.alarm_thread.start()

        # Atualizar relógio e temperatura periodicamente
        self.update_clock()
        self.update_weather()

    def create_weather_bar(self):
        weather_frame = tk.Frame(self.main_frame, bg=self.colors["background"])
        weather_frame.pack(fill="x", pady=(5, 10))
        
        self.weather_icon = tk.Label(
            weather_frame,
            text=self.weather_data["icon"],
            font=("Helvetica", 20),
            fg=self.colors["primary"],
            bg=self.colors["background"],
        )
        self.weather_icon.pack(side="left", padx=(20, 5))
        
        self.temp_label = tk.Label(
            weather_frame,
            text=f"{self.weather_data['temperature']}°C",
            font=SCREEN_CONFIG["font_temp"],
            fg=self.colors["text"],
            bg=self.colors["background"],
        )
        self.temp_label.pack(side="left", padx=(0, 20))
        
        # Previsão simples
        weather_desc = {
            "sunny": "Ensolarado",
            "partly_cloudy": "Parc. Nublado",
            "cloudy": "Nublado",
            "rainy": "Chuvoso"
        }
        
        self.weather_desc = tk.Label(
            weather_frame,
            text=weather_desc[self.weather_data["condition"]],
            font=SCREEN_CONFIG["font_temp"],
            fg=self.colors["text_secondary"],
            bg=self.colors["background"],
        )
        self.weather_desc.pack(side="right", padx=(0, 20))

    def update_weather(self):
        # Atualizar dados meteorológicos a cada 30 minutos
        if int(datetime.now().strftime("%M")) % 30 == 0:  # A cada 30 minutos
            self.weather_data = WeatherService.get_weather()
            
            self.weather_icon.config(text=self.weather_data["icon"])
            self.temp_label.config(text=f"{self.weather_data['temperature']}°C")
            
            weather_desc = {
                "sunny": "Ensolarado",
                "partly_cloudy": "Parc. Nublado",
                "cloudy": "Nublado",
                "rainy": "Chuvoso"
            }
            self.weather_desc.config(text=weather_desc[self.weather_data["condition"]])
        
        self.root.after(60000, self.update_weather)  # Verificar a cada minuto

    def show_alarm_list(self):
        AlarmListDialog(self)

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