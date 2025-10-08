#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PiClock Touch – Relógio com alarme e clima melhorado
"""

import requests
import os
import json
import uuid
import threading
import time
from datetime import datetime, date, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from dotenv import load_dotenv

# ====== CONFIGURAÇÕES ======
load_dotenv()
FULLSCREEN = False
ALARM_FILE = "alarms.json"
REFRESH_CLOCK_MS = 1000
REFRESH_WEATHER_MS = 10 * 60 * 1000
CHECK_ALARMS_MS = 1000

OWM_API_KEY = os.environ.get("OWM_API_KEY", "")
CITY = "São Paulo"
COUNTRY_CODE = "BR"

PT_WEEKDAYS = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo"
]
PT_WEEKDAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
PT_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]

UBIDOTS_TOKEN = os.environ.get("UBIDOTS_TOKEN", "")
UBIDOTS_DEVICE = "piclock"  # nome que aparecerá no Ubidots

# ====== ÁUDIO ======
try:
    from audio import AudioPlayer
except Exception:
    class AudioPlayer:
        def __init__(self):
            self.playing = False
        def play(self, filepath=None, loop=True):
            self.playing = True
            print("[DEBUG] Alarme tocando (simulado)")
        def stop(self):
            self.playing = False
            print("[DEBUG] Alarme parado (simulado)")
        def is_playing(self):
            return self.playing
        @staticmethod
        def set_volume(percent: int):
            pass

# ====== UTIL ======
from urllib.request import urlopen
from urllib.error import URLError
import json as _json

def http_get_json(url: str):
    try:
        with urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return _json.loads(data)
    except Exception:
        return None
    
# ====== UBIDOTS ======
def ubidots_send_batch(data: dict):
    """Envia várias variáveis de uma vez para o Ubidots (Industrial API)"""
    if not UBIDOTS_TOKEN:
        print("[ERRO] Token do Ubidots não encontrado.")
        return False

    success = True
    for variable, info in data.items():
        value = info.get("value")
        payload = {"value": value}
        url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE}/{variable}/values"
        headers = {
            "X-Auth-Token": UBIDOTS_TOKEN,
            "Content-Type": "application/json"
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code < 400:
                print(f"[OK] Ubidots: {variable} = {value}")
            else:
                print(f"[ERRO] Ubidots ({resp.status_code}): {resp.text}")
                success = False
        except Exception as e:
            print(f"[EXCEÇÃO] Ubidots: {e}")
            success = False
    return success

def ubidots_get_last_value(variable: str):
    """Obtém o último valor de uma variável do Ubidots."""
    if not UBIDOTS_TOKEN:
        return None
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{UBIDOTS_DEVICE}/{variable}/values"
    headers = {"X-Auth-Token": UBIDOTS_TOKEN}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("results"):
                return data["results"][0]["value"]
    except Exception as e:
        print(f"[EXCEÇÃO] Ubidots GET: {e}")
    return None


# ====== CLIMA ======
def weather_icon_from_owm(main: str, descr: str) -> str:
    m = (main or "").lower()
    d = (descr or "").lower()
    if "thunder" in m or "trovoada" in d:
        return "⛈️"
    if "drizzle" in m or "garoa" in d:
        return "🌦️"
    if "rain" in m or "chuva" in d:
        return "🌧️"
    if "snow" in m or "neve" in d:
        return "❄️"
    if "cloud" in m or "nublado" in d or "nuv" in d:
        return "☁️"
    if "clear" in m or "céu limpo" in d:
        return "☀️"
    if "mist" in m or "fog" in m or "nebl" in d:
        return "🌫️"
    return "🌡️"

def fetch_weather(city: str, country: str, api_key: str):
    if not api_key:
        return {
            "temp": "—",
            "descr": "Sem API Key",
            "icon": "🌡️",
            "temp_min": "—",
            "temp_max": "—"
        }

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": f"{city},{country}",
        "appid": api_key,
        "units": "metric",
        "lang": "pt_br"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200 or "main" not in data or "weather" not in data:
            return {
                "temp": "—",
                "descr": "Erro ao obter clima",
                "icon": "🌡️",
                "temp_min": "—",
                "temp_max": "—"
            }

        temp = round(data["main"]["temp"])
        temp_min = round(data["main"]["temp_min"])
        temp_max = round(data["main"]["temp_max"])
        descr = data["weather"][0]["description"]
        icon = weather_icon_from_owm(data["weather"][0]["main"], descr)

        return {
            "temp": temp,
            "descr": descr,
            "icon": icon,
            "temp_min": temp_min,
            "temp_max": temp_max
        }

    except Exception as e:
        print(f"[EXCEÇÃO] Erro ao obter clima: {e}")
        return {
            "temp": "—",
            "descr": "Falha de conexão",
            "icon": "🌡️",
            "temp_min": "—",
            "temp_max": "—"
        }


# ====== MODELO ======
class Alarm:
    def __init__(self, alarm_id: str, hour: int, minute: int, days: list[int], enabled: bool = True):
        self.id = alarm_id
        self.hour = hour
        self.minute = minute
        self.days = days
        self.enabled = enabled
        self._last_trigger_key = None

    @staticmethod
    def from_dict(d: dict):
        return Alarm(
            d.get("id", str(uuid.uuid4())),
            int(d.get("hour", 7)),
            int(d.get("minute", 0)),
            list(d.get("days", [])),
            bool(d.get("enabled", True)),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "hour": self.hour,
            "minute": self.minute,
            "days": self.days,
            "enabled": self.enabled,
        }

    def matches_now(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        weekday = now.weekday()
        if weekday not in self.days:
            return False
        hm = (now.hour, now.minute)
        key = f"{date.today().isoformat()}-{hm[0]:02d}:{hm[1]:02d}"
        if hm == (self.hour, self.minute) and self._last_trigger_key != key:
            self._last_trigger_key = key
            return True
        return False

    def human_time(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"

    def human_days(self) -> str:
        if set(self.days) == set(range(7)):
            return "Todos os dias"
        return ", ".join(PT_WEEKDAYS_SHORT[d] for d in sorted(self.days))

class AlarmStore:
    def __init__(self, path: str):
        self.path = path
        self.alarms: list[Alarm] = []
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self.alarms = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.alarms = [Alarm.from_dict(a) for a in data.get("alarms", [])]
        except Exception:
            self.alarms = []

    def save(self):
        data = {"alarms": [a.to_dict() for a in self.alarms]}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def add(self, hour: int, minute: int, days: list[int]):
        a = Alarm(str(uuid.uuid4()), hour, minute, days, True)
        self.alarms.append(a)
        self.save()
        return a

    def delete(self, alarm_id: str):
        self.alarms = [a for a in self.alarms if a.id != alarm_id]
        self.save()

    def get_next_alarm(self, now: datetime):
        """Retorna o próximo alarme futuro."""
        future_alarms = []
        for a in self.alarms:
            if not a.enabled:
                continue
            for offset in range(7):  # até 1 semana adiante
                d = now + timedelta(days=offset)
                if d.weekday() in a.days:
                    candidate_time = datetime(d.year, d.month, d.day, a.hour, a.minute)
                    if candidate_time > now:
                        future_alarms.append((candidate_time, a))
        if not future_alarms:
            return None
        return min(future_alarms, key=lambda x: x[0])[1]

# ====== APP ======
class PiClockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PiClock Touch")
        self.geometry("800x480")
        if FULLSCREEN:
            self.attributes("-fullscreen", True)

        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.configure(bg="#0a0a0a")

        self.base_font_size = 12
        self.fonts = {}
        self._build_fonts(scale=1.0)
        self.bind("<Configure>", self._on_configure)

        self.store = AlarmStore(ALARM_FILE)
        self.audio = AudioPlayer()
        self.weather = None

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(0, weight=1)

        self.frames = {}
        for F in (MainScreen, NewAlarmScreen, ListAlarmsScreen):
            frame = F(parent=self.container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainScreen")

        self.after(REFRESH_CLOCK_MS, self._tick_clock)
        self.after(CHECK_ALARMS_MS, self._tick_alarms)
        self.after(100, self._tick_weather)
        self.after(5000, self._tick_remote_commands)

    def _build_fonts(self, scale: float):
        import tkinter.font as tkfont
        self.fonts["clock"] = tkfont.Font(family="DejaVu Sans", size=int(72 * scale), weight="bold")
        self.fonts["date"] = tkfont.Font(family="DejaVu Sans", size=int(22 * scale))
        self.fonts["weather_temp"] = tkfont.Font(family="DejaVu Sans", size=int(32 * scale), weight="bold")
        self.fonts["weather_descr"] = tkfont.Font(family="DejaVu Sans", size=int(16 * scale))
        self.fonts["button"] = tkfont.Font(family="DejaVu Sans", size=int(18 * scale), weight="bold")
        self.fonts["list"] = tkfont.Font(family="DejaVu Sans", size=int(16 * scale))
        self.fonts["title"] = tkfont.Font(family="DejaVu Sans", size=int(24 * scale), weight="bold")

    def _on_configure(self, event):
        h = max(self.winfo_height(), 1)
        scale = max(min(h / 480.0, 2.0), 0.6)
        self._build_fonts(scale)
        for f in self.frames.values():
            if hasattr(f, "on_scale_change"):
                f.on_scale_change()

    def show_frame(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    def _tick_clock(self):
        main: MainScreen = self.frames.get("MainScreen")  # type: ignore
        if main:
            main.update_clock()
        self.after(REFRESH_CLOCK_MS, self._tick_clock)

    def _tick_weather(self):
        self.weather = fetch_weather(CITY, COUNTRY_CODE, OWM_API_KEY)
        main: MainScreen = self.frames.get("MainScreen")  # type: ignore
        if main:
            main.update_weather()
        self.after(REFRESH_WEATHER_MS, self._tick_weather)

    def _tick_alarms(self):
        now = datetime.now()
        for a in self.store.alarms:
            try:
                if a.matches_now(now):
                    self.start_alarm()
            except Exception:
                pass
        self.after(CHECK_ALARMS_MS, self._tick_alarms)

    def start_alarm(self):
        if not self.audio.is_playing():
            self.audio.play()
        main: MainScreen = self.frames.get("MainScreen")
        if main:
            main.set_alarm_state(True)
            main.update_test_btn()

        now = datetime.now()
        payload = {
            "alarme_event": {"value": 1},
            "alarmes_tocados_total": {"value": 1, "context": {"hora": now.strftime("%H:%M")}},
            "alarme_hora": {"value": now.hour},
            "alarme_minuto": {"value": now.minute},
            "date_year": {"value": now.year},
            "date_month": {"value": now.month},
            "date_day": {"value": now.day},
            "timestamp": {"value": int(time.time())},
        }
        ubidots_send_batch(payload)

    def stop_alarm(self):
        if self.audio.is_playing():
            self.audio.stop()
        main: MainScreen = self.frames.get("MainScreen")
        if main:
            main.set_alarm_state(False)
            main.update_test_btn()

        ubidots_send_batch({"alarme_event": {"value": 0}})

    def snooze_alarm(self):
        now = datetime.now()
        snooze_time = now + timedelta(minutes=5)
        self.store.add(snooze_time.hour, snooze_time.minute, [snooze_time.weekday()])
        messagebox.showinfo("Adiar Alarme", f"Alarme adiado para {snooze_time.strftime('%H:%M')}")
        self.stop_alarm()

        payload = {
            "alarme_soneca": {"value": 1, "context": {"nova_hora": snooze_time.strftime("%H:%M")}},
            "date_year": {"value": snooze_time.year},
            "date_month": {"value": snooze_time.month},
            "date_day": {"value": snooze_time.day},
            "date_hour": {"value": snooze_time.hour},
            "date_minute": {"value": snooze_time.minute},
            "timestamp": {"value": int(time.time())},
        }
        ubidots_send_batch(payload)

    def _tick_remote_commands(self):
        """Verifica se o Ubidots enviou comando remoto de disparar alarme."""
        value = ubidots_get_last_value("remote_alarm_trigger")
        if value == 1:
            print("[UBIDOTS] Comando remoto recebido: tocar alarme")
            self.start_alarm()
            # Reseta a variável para 0 (evita repetir)
            ubidots_send_batch({"remote_alarm_trigger": {"value": 0}})
        self.after(5000, self._tick_remote_commands)

# ====== TELAS ======
class MainScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)

        self.style = ttk.Style(self)
        self.style.configure("Main.TFrame", background="#0a0a0a")
        self.style.configure("Main.TLabel", background="#0a0a0a", foreground="#f7f7f7")
        self.style.configure("Action.TButton", padding=12)

        self.clock_lbl = ttk.Label(self, text="00:00", style="Main.TLabel")
        self.clock_lbl.grid(row=0, column=0, pady=(20, 0))

        self.date_lbl = ttk.Label(self, text="", style="Main.TLabel")
        self.date_lbl.grid(row=1, column=0, pady=(0, 10))

        self.weather_card = ttk.Frame(self, style="Main.TFrame")
        self.weather_card.grid(row=2, column=0, pady=(0, 10))
        self.weather_icon_lbl = ttk.Label(self.weather_card, text="🌡️", style="Main.TLabel")
        self.weather_temp_lbl = ttk.Label(self.weather_card, text="—°C", style="Main.TLabel")
        self.weather_descr_lbl = ttk.Label(self.weather_card, text="", style="Main.TLabel")
        self.weather_extra_lbl = ttk.Label(self.weather_card, text="", style="Main.TLabel")
        self.weather_icon_lbl.grid(row=0, column=0, padx=8)
        self.weather_temp_lbl.grid(row=0, column=1, padx=8)
        self.weather_descr_lbl.grid(row=1, column=0, columnspan=2)
        self.weather_extra_lbl.grid(row=2, column=0, columnspan=2)

        self.next_alarm_lbl = ttk.Label(self, text="Próximo alarme: —", style="Main.TLabel")
        self.next_alarm_lbl.grid(row=3, column=0, pady=(10, 0))

        actions = ttk.Frame(self, style="Main.TFrame")
        actions.grid(row=4, column=0, pady=12)
        for i in range(5):
            actions.columnconfigure(i, weight=1)

        self.new_alarm_btn = ttk.Button(actions, text="Novo alarme", style="Action.TButton",
                                        command=lambda: self.controller.show_frame("NewAlarmScreen"))
        self.list_alarms_btn = ttk.Button(actions, text="Alarmes", style="Action.TButton",
                                          command=lambda: self.controller.show_frame("ListAlarmsScreen"))
        self.test_btn = ttk.Button(actions, text="Testar alarme", style="Action.TButton",
                                   command=self._toggle_test)
        self.stop_alarm_btn = ttk.Button(actions, text="Parar alarme", style="Action.TButton",
                                         command=self.controller.stop_alarm, state="disabled")
        self.snooze_btn = ttk.Button(actions, text="Adiar Alarme (5 min)", style="Action.TButton",
                                     command=self.controller.snooze_alarm, state="disabled")

        self.new_alarm_btn.grid(row=0, column=0, padx=6)
        self.list_alarms_btn.grid(row=0, column=1, padx=6)
        self.test_btn.grid(row=0, column=2, padx=6)
        self.stop_alarm_btn.grid(row=0, column=3, padx=6)
        self.snooze_btn.grid(row=0, column=4, padx=6)

        self.on_scale_change()
        self.update_clock()
        self.update_weather()

    def on_scale_change(self):
        f = self.controller.fonts
        self.clock_lbl.configure(font=f["clock"])
        self.date_lbl.configure(font=f["date"])
        self.weather_icon_lbl.configure(font=f["weather_temp"])
        self.weather_temp_lbl.configure(font=f["weather_temp"])
        self.weather_descr_lbl.configure(font=f["weather_descr"])
        self.weather_extra_lbl.configure(font=f["weather_descr"])

    def on_show(self):
        self.update_clock()
        self.update_weather()
        self.update_test_btn()

    def update_test_btn(self):
        txt = "Parar teste" if self.controller.audio.is_playing() else "Testar alarme"
        self.test_btn.configure(text=txt)

    def _toggle_test(self):
        if self.controller.audio.is_playing():
            self.controller.audio.stop()
        else:
            self.controller.audio.play()
        self.update_test_btn()

    def set_alarm_state(self, active: bool):
        self.stop_alarm_btn.configure(state=("normal" if active else "disabled"))
        self.snooze_btn.configure(state=("normal" if active else "disabled"))

    def update_clock(self):
        now = datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M"))
        dow = PT_WEEKDAYS[now.weekday()]
        date_str = f"{now.day} de {PT_MONTHS[now.month-1]} de {now.year}"
        self.date_lbl.configure(text=f"{dow}, {date_str}")

        next_alarm = self.controller.store.get_next_alarm(now)
        if next_alarm:
            self.next_alarm_lbl.configure(text=f"Próximo alarme: {next_alarm.human_time()} ({next_alarm.human_days()})")
        else:
            self.next_alarm_lbl.configure(text="Próximo alarme: —")

    def update_weather(self):
        w = self.controller.weather
    
        if not w:
            self.weather_icon_lbl.configure(text="🌡️")
            self.weather_temp_lbl.configure(text="—°C")
            self.weather_descr_lbl.configure(text="Sem dados")
            self.weather_extra_lbl.configure(text="Mín: —°C / Máx: —°C")
        else:
            temp = w.get("temp", "—")
            temp_min = w.get("temp_min", "—")
            temp_max = w.get("temp_max", "—")
            descr = w.get("descr", "—")
            icon = w.get("icon", "🌡️")
    
            self.weather_icon_lbl.configure(text=icon)
            self.weather_temp_lbl.configure(text=f"{temp}°C")
            self.weather_descr_lbl.configure(text=descr.capitalize())
            self.weather_extra_lbl.configure(
                text=f"Mín: {temp_min}°C / Máx: {temp_max}°C"
            )
    
            # >>> Envia pacote completo para o Ubidots
            now = datetime.now()
            payload = {
                "temperature": {"value": temp},
                "temp_min": {"value": temp_min},
                "temp_max": {"value": temp_max},
                "humidity": {"value": w.get("humidity", 0)},
                "pressure": {"value": w.get("pressure", 0)},
                "weather_descr": {"value": 0, "context": {"descr": descr}},
                "weather_code": {"value": hash(descr) % 100},  # código simplificado
                "date_year": {"value": now.year},
                "date_month": {"value": now.month},
                "date_day": {"value": now.day},
                "date_hour": {"value": now.hour},
                "date_minute": {"value": now.minute},
                "timestamp": {"value": int(time.time())},
            }
            ubidots_send_batch(payload)

# ====== Nova tela: criação de alarmes ======
class NewAlarmScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(self, text="Novo alarme", style="Main.TLabel")
        self.title_lbl.grid(row=0, column=0, pady=(16, 8))

        form = ttk.Frame(self, style="Main.TFrame")
        form.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self.hour_var = tk.StringVar(value="07")
        self.min_var = tk.StringVar(value="00")
        self.hour_sb = ttk.Spinbox(form, from_=0, to=23, textvariable=self.hour_var, width=4, wrap=True, format="%02.0f")
        self.min_sb = ttk.Spinbox(form, from_=0, to=59, textvariable=self.min_var, width=4, wrap=True, format="%02.0f")
        ttk.Label(form, text="Hora:", style="Main.TLabel").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        self.hour_sb.grid(row=0, column=1, sticky="w", padx=8, pady=8)
        ttk.Label(form, text="Min:", style="Main.TLabel").grid(row=1, column=0, sticky="e", padx=8, pady=8)
        self.min_sb.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        days_frame = ttk.Frame(form, style="Main.TFrame")
        days_frame.grid(row=2, column=0, columnspan=2, pady=(8, 12))
        self.day_vars = []
        for i, name in enumerate(PT_WEEKDAYS_SHORT):
            var = tk.IntVar(value=1 if i < 5 else 0)
            cb = ttk.Checkbutton(days_frame, text=name, variable=var, style="Main.TCheckbutton")
            cb.grid(row=0, column=i, padx=6, pady=4)
            self.day_vars.append(var)

        actions = ttk.Frame(self, style="Main.TFrame")
        actions.grid(row=3, column=0, pady=12)
        save_btn = ttk.Button(actions, text="Salvar", command=self._save)
        cancel_btn = ttk.Button(actions, text="Cancelar", command=lambda: self.controller.show_frame("MainScreen"))
        save_btn.grid(row=0, column=0, padx=8)
        cancel_btn.grid(row=0, column=1, padx=8)

        self.on_scale_change()

    def on_scale_change(self):
        f = self.controller.fonts
        self.title_lbl.configure(font=f["title"])
        self.hour_sb.configure(font=f["list"])
        self.min_sb.configure(font=f["list"])

    def _save(self):
        try:
            hour = int(self.hour_var.get())
            minute = int(self.min_var.get())
        except ValueError:
            messagebox.showerror("Erro", "Hora/minuto inválidos")
            return
        days = [i for i, v in enumerate(self.day_vars) if v.get() == 1]
        if not days:
            if not messagebox.askyesno("Sem dias", "Nenhum dia selecionado. Deseja mesmo salvar?"):
                return
        self.controller.store.add(hour, minute, days)
        messagebox.showinfo("Salvo", "Alarme criado!")
        self.controller.show_frame("ListAlarmsScreen")

# ====== Tela de listagem de alarmes ======
class ListAlarmsScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.title_lbl = ttk.Label(self, text="Alarmes", style="Main.TLabel")
        self.title_lbl.grid(row=0, column=0, pady=(16, 8))

        table_frame = ttk.Frame(self, style="Main.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=16)
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("time", "days")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("time", text="Hora")
        self.tree.heading("days", text="Dias")
        self.tree.column("time", width=120, anchor="center")
        self.tree.column("days", width=400, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        actions = ttk.Frame(self, style="Main.TFrame")
        actions.grid(row=2, column=0, pady=12)
        del_btn = ttk.Button(actions, text="Excluir selecionado", command=self._delete_selected)
        back_btn = ttk.Button(actions, text="Voltar", command=lambda: self.controller.show_frame("MainScreen"))
        del_btn.grid(row=0, column=0, padx=8)
        back_btn.grid(row=0, column=1, padx=8)

        self.on_scale_change()

    def on_show(self):
        self.refresh()

    def on_scale_change(self):
        f = self.controller.fonts
        self.title_lbl.configure(font=f["title"])
        style = ttk.Style(self)
        style.configure("Treeview", font=f["list"], rowheight=int(f["list"].cget("size")) + 14)
        style.configure("Treeview.Heading", font=f["list"])

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for a in self.controller.store.alarms:
            self.tree.insert("", "end", iid=a.id, values=(a.human_time(), a.human_days()))

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleção", "Selecione um alarme para excluir")
            return
        alarm_id = sel[0]
        if messagebox.askyesno("Confirmar", "Excluir este alarme?"):
            self.controller.store.delete(alarm_id)
            self.refresh()

# ====== MAIN ======
if __name__ == "__main__":
    app = PiClockApp()
    app.mainloop()

