#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PiClock Touch – Relógio com alarme e clima

Hardware:
- Raspberry Pi 3
- Display oficial Raspberry Pi 7" (800x480)
- Buzzer no GPIO 23 (BCM) – já há a classe AudioPlayer do usuário

Funcionalidades:
- Tela inicial com relógio (HH:MM), dia da semana + data, temperatura atual e ícone textual do clima.
- Botão para criar novo alarme (dia(s) da semana e horário).
- Tela de listagem de alarmes com exclusão.
- Disparo de alarme via buzzer (classe AudioPlayer).
- Layout responsivo ao tamanho da janela (otimizado para 800x480).

Como usar:
1) Opcional: Defina sua cidade/país e API key do OpenWeather (gratuita) nas CONSTANTES abaixo.
2) Execute:  python3 piclock.py
3) Toque nos botões para criar/gerenciar alarmes. Quando o alarme tocar, use "Parar alarme".

Observações:
- Se não configurar a API de clima, o app mostra "—".
- Dias de semana em pt-BR; alarmes se repetem toda semana nos dias selecionados.
- Para iniciar em tela cheia, altere FULLSCREEN = True.
"""

import os
import json
import uuid
import threading
import time
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox

# ====== CONFIGURAÇÕES ======
FULLSCREEN = False              # True = tela cheia
ALARM_FILE = "alarms.json"      # onde os alarmes ficam salvos
REFRESH_CLOCK_MS = 1000         # atualização do relógio (ms)
REFRESH_WEATHER_MS = 10 * 60 * 1000  # clima a cada 10 minutos
CHECK_ALARMS_MS = 1000          # checar alarme a cada 1 s

# Clima (OpenWeatherMap). Se não tiver API, deixar vazio e definir CITY/COUNTRY_CODE mesmo assim.
OWM_API_KEY = ""  # ex: "abc123..."  (https://openweathermap.org/api)
CITY = "São Paulo"
COUNTRY_CODE = "BR"

# Mapeamentos de data (pt-BR)
PT_WEEKDAYS = [
    "segunda-feira", "terça-feira", "quarta-feira",
    "quinta-feira", "sexta-feira", "sábado", "domingo"
]  # Python weekday(): seg=0 ... dom=6
PT_WEEKDAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
PT_MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
]

# ====== ÁUDIO (BUZZER) ======
# Tenta importar a classe existente do usuário; se falhar, define um fallback "silencioso".
try:
    from audio_player import AudioPlayer  # ajuste o nome do módulo se necessário
except Exception:
    try:
        # Recria a classe com gpiozero, caso esteja disponível
        from gpiozero import Buzzer
        import threading as _threading
        BUZZER_PIN = 23
        class AudioPlayer:
            def __init__(self):
                self.buzzer = Buzzer(BUZZER_PIN)
                self.playing = False
                self.thread = None
            def play(self, filepath=None, loop=True):
                self.stop()
                self.playing = True
                self.thread = _threading.Thread(target=self._buzz_loop, daemon=True)
                self.thread.start()
            def _buzz_loop(self):
                while self.playing:
                    self.buzzer.on(); time.sleep(0.5)
                    self.buzzer.off(); time.sleep(0.5)
            def stop(self):
                self.playing = False
                if self.thread:
                    self.thread.join(timeout=0.1)
                try:
                    self.buzzer.off()
                except Exception:
                    pass
            def is_playing(self):
                return self.playing
            @staticmethod
            def set_volume(percent: int):
                pass
    except Exception:
        # Fallback sem hardware: apenas marca estado.
        class AudioPlayer:
            def __init__(self):
                self.playing = False
            def play(self, filepath=None, loop=True):
                self.playing = True
                print("[DEBUG] (simulado) Alarme tocando...")
            def stop(self):
                if self.playing:
                    print("[DEBUG] (simulado) Alarme parado.")
                self.playing = False
            def is_playing(self):
                return self.playing
            @staticmethod
            def set_volume(percent: int):
                pass

# ====== UTIL: Rede sem requests (urllib)
from urllib.request import urlopen
from urllib.error import URLError
import json as _json

def http_get_json(url: str):
    try:
        with urlopen(url, timeout=5) as resp:
            data = resp.read().decode("utf-8")
            return _json.loads(data)
    except URLError:
        return None
    except Exception:
        return None

# ====== CLIMA ======

def weather_icon_from_owm(main: str, descr: str) -> str:
    m = (main or "").lower()
    d = (descr or "").lower()
    # Ícones de texto/emoji leves para não depender de imagens
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
    """Retorna dados FIXOS de clima conforme solicitado: nublado 19ºC."""
    return {"temp": 19, "descr": "nublado", "icon": "☁️"}

# ====== MODELO DE DADOS ======
class Alarm:
    def __init__(self, alarm_id: str, hour: int, minute: int, days: list[int], enabled: bool = True):
        self.id = alarm_id
        self.hour = hour
        self.minute = minute
        self.days = days[:]  # lista de inteiros 0..6 (seg=0 ... dom=6)
        self.enabled = enabled
        # Não persistimos; usado para evitar disparo repetido no mesmo minuto
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
        weekday = now.weekday()  # seg=0 ... dom=6
        if weekday not in self.days:
            return False
        hm = (now.hour, now.minute)
        key = f"{date.today().isoformat()}-{hm[0]:02d}:{hm[1]:02d}"
        # Evita repetir dentro do mesmo minuto
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

# ====== UI ======
class PiClockApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PiClock Touch")
        self.geometry("800x480")
        if FULLSCREEN:
            self.attributes("-fullscreen", True)

        # Estilos base
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.configure(bg="#0a0a0a")

        # Escala de fontes dinâmica
        self.base_font_size = 12
        self.fonts = {}
        self._build_fonts(scale=1.0)
        self.bind("<Configure>", self._on_configure)

        # Dados
        self.store = AlarmStore(ALARM_FILE)
        self.audio = AudioPlayer()
        self.weather = None

        # Container de telas
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

        # Loops periódicos
        self.after(REFRESH_CLOCK_MS, self._tick_clock)
        self.after(CHECK_ALARMS_MS, self._tick_alarms)
        self.after(100, self._tick_weather)  # carrega logo após iniciar

    # --------- Escala de fontes ---------
    def _build_fonts(self, scale: float):
        import tkinter.font as tkfont
        self.fonts["clock"] = tkfont.Font(family="DejaVu Sans", size=int(64 * scale), weight="bold")
        self.fonts["date"] = tkfont.Font(family="DejaVu Sans", size=int(20 * scale))
        self.fonts["weather_temp"] = tkfont.Font(family="DejaVu Sans", size=int(36 * scale), weight="bold")
        self.fonts["weather_descr"] = tkfont.Font(family="DejaVu Sans", size=int(18 * scale))
        self.fonts["button"] = tkfont.Font(family="DejaVu Sans", size=int(18 * scale), weight="bold")
        self.fonts["list"] = tkfont.Font(family="DejaVu Sans", size=int(16 * scale))
        self.fonts["title"] = tkfont.Font(family="DejaVu Sans", size=int(24 * scale), weight="bold")

    def _on_configure(self, event):
        # Ajusta escala com base na altura (pensado para 480 de base)
        h = max(self.winfo_height(), 1)
        scale = max(min(h / 480.0, 2.0), 0.6)
        self._build_fonts(scale)
        # Notifica telas para reajustar estilos se necessário
        for f in self.frames.values():
            if hasattr(f, "on_scale_change"):
                f.on_scale_change()

    # --------- Navegação ---------
    def show_frame(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
        if hasattr(frame, "on_show"):
            frame.on_show()

    # --------- Ticks ---------
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

    # --------- Alarme ---------
    def start_alarm(self):
        if not self.audio.is_playing():
            self.audio.play()
        main: MainScreen = self.frames.get("MainScreen")  # type: ignore
        if main:
            main.set_alarm_state(True)
            main.update_test_btn()

    def stop_alarm(self):
        if self.audio.is_playing():
            self.audio.stop()
        main: MainScreen = self.frames.get("MainScreen")  # type: ignore
        if main:
            main.set_alarm_state(False)
            main.update_test_btn()

# ====== Telas ======
class MainScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=3)  # relógio grande
        self.rowconfigure(1, weight=2)  # clima + data
        self.rowconfigure(2, weight=1)  # botões

        # Estilos
        self.style = ttk.Style(self)
        self.style.configure("Main.TFrame", background="#0a0a0a")
        self.style.configure("Card.TFrame", background="#111")
        self.style.configure("Card.TLabel", background="#111", foreground="#eee")
        self.style.configure("Main.TLabel", background="#0a0a0a", foreground="#f7f7f7")
        self.style.configure("Action.TButton", padding=12)

        # Relógio (centro)
        self.clock_lbl = ttk.Label(self, text="00:00", style="Main.TLabel")
        self.clock_lbl.grid(row=0, column=0, sticky="n", pady=(20, 0))

        # Linha: Data + Clima
        info = ttk.Frame(self, style="Main.TFrame")
        info.grid(row=1, column=0, sticky="nsew", padx=16, pady=10)
        info.columnconfigure(0, weight=1)
        info.columnconfigure(1, weight=1)

        # Data
        self.date_lbl = ttk.Label(info, text="", style="Main.TLabel")
        self.date_lbl.grid(row=0, column=0, sticky="w")

        # Cartão de clima
        self.weather_card = ttk.Frame(info, style="Card.TFrame")
        self.weather_card.grid(row=0, column=1, sticky="e", padx=8)
        for c in range(2):
            self.weather_card.columnconfigure(c, weight=0)
        self.weather_icon_lbl = ttk.Label(self.weather_card, text="🌡️", style="Card.TLabel")
        self.weather_temp_lbl = ttk.Label(self.weather_card, text="—°C", style="Card.TLabel")
        self.weather_descr_lbl = ttk.Label(self.weather_card, text="", style="Card.TLabel")
        self.weather_icon_lbl.grid(row=0, column=0, sticky="w", padx=10, pady=8)
        self.weather_temp_lbl.grid(row=0, column=1, sticky="w", padx=10)
        self.weather_descr_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0,10))

        # Botões de ação
        actions = ttk.Frame(self, style="Main.TFrame")
        actions.grid(row=2, column=0, pady=8)
        for i in range(4):
            actions.columnconfigure(i, weight=1)

        self.new_alarm_btn = ttk.Button(actions, text="Novo alarme", style="Action.TButton",
                                        command=lambda: self.controller.show_frame("NewAlarmScreen"))
        self.list_alarms_btn = ttk.Button(actions, text="Alarmes", style="Action.TButton",
                                          command=lambda: self.controller.show_frame("ListAlarmsScreen"))
        self.test_btn = ttk.Button(actions, text="Testar alarme", style="Action.TButton",
                                         command=self._toggle_test)
        self.stop_alarm_btn = ttk.Button(actions, text="Parar alarme", style="Action.TButton",
                                         command=self.controller.stop_alarm, state="disabled")
        self.new_alarm_btn.grid(row=0, column=0, padx=8)
        self.list_alarms_btn.grid(row=0, column=1, padx=8)
        self.test_btn.grid(row=0, column=2, padx=8)
        self.stop_alarm_btn.grid(row=0, column=3, padx=8)

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
        self.new_alarm_btn.configure(style="Action.TButton")
        self.list_alarms_btn.configure(style="Action.TButton")
        self.stop_alarm_btn.configure(style="Action.TButton")

    def on_show(self):
        # Atualiza info ao voltar
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

    def update_clock(self):
        now = datetime.now()
        self.clock_lbl.configure(text=now.strftime("%H:%M"))
        dow = PT_WEEKDAYS[now.weekday()]
        date_str = f"{now.day} de {PT_MONTHS[now.month-1]} de {now.year}"
        self.date_lbl.configure(text=f"{dow}, {date_str}")

    def update_weather(self):
        w = self.controller.weather
        if not w:
            self.weather_icon_lbl.configure(text="🌡️")
            self.weather_temp_lbl.configure(text="—°C")
            self.weather_descr_lbl.configure(text="")
        else:
            self.weather_icon_lbl.configure(text=w["icon"]) 
            self.weather_temp_lbl.configure(text=f"{w['temp']}°C")
            self.weather_descr_lbl.configure(text=w["descr"].capitalize())


class NewAlarmScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)

        self.title_lbl = ttk.Label(self, text="Novo alarme", style="Main.TLabel")
        self.title_lbl.grid(row=0, column=0, pady=(16, 8))

        form = ttk.Frame(self, style="Card.TFrame")
        form.grid(row=1, column=0, padx=16, pady=8, sticky="nsew")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        # Hora / Minuto
        self.hour_var = tk.StringVar(value="07")
        self.min_var = tk.StringVar(value="00")
        self.hour_sb = ttk.Spinbox(form, from_=0, to=23, textvariable=self.hour_var, width=4, wrap=True, format="%02.0f")
        self.min_sb = ttk.Spinbox(form, from_=0, to=59, textvariable=self.min_var, width=4, wrap=True, format="%02.0f")
        ttk.Label(form, text="Hora:", style="Card.TLabel").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        self.hour_sb.grid(row=0, column=1, sticky="w", padx=8, pady=8)
        ttk.Label(form, text="Min:", style="Card.TLabel").grid(row=1, column=0, sticky="e", padx=8, pady=8)
        self.min_sb.grid(row=1, column=1, sticky="w", padx=8, pady=8)

        # Dias da semana (seg=0 ... dom=6)
        days_frame = ttk.Frame(form, style="Card.TFrame")
        days_frame.grid(row=2, column=0, columnspan=2, pady=(8, 12))
        self.day_vars = []
        for i, name in enumerate(PT_WEEKDAYS_SHORT):
            var = tk.IntVar(value=1 if i < 5 else 0)  # por padrão: seg-sex
            cb = ttk.Checkbutton(days_frame, text=name, variable=var)
            cb.grid(row=0, column=i, padx=6, pady=4)
            self.day_vars.append(var)

        # Botões
        actions = ttk.Frame(self, style="Main.TFrame")
        actions.grid(row=2, column=0, pady=12)
        save_btn = ttk.Button(actions, text="Salvar", command=self._save)
        cancel_btn = ttk.Button(actions, text="Cancelar", command=lambda: self.controller.show_frame("MainScreen"))
        save_btn.grid(row=0, column=0, padx=8)
        cancel_btn.grid(row=0, column=1, padx=8)

        self.on_scale_change()

    def on_scale_change(self):
        f = self.controller.fonts
        self.title_lbl.configure(font=f["title"]) 
        for w in (self.hour_sb, self.min_sb):
            w.configure(font=f["list"])  

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


class ListAlarmsScreen(ttk.Frame):
    def __init__(self, parent, controller: PiClockApp):
        super().__init__(parent)
        self.controller = controller
        self.configure(style="Main.TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.title_lbl = ttk.Label(self, text="Alarmes", style="Main.TLabel")
        self.title_lbl.grid(row=0, column=0, pady=(16, 8))

        # Tabela
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

        # Botões
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
        # Treeview fonte
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
