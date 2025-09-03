import time
import threading

class AudioPlayer:
    def __init__(self, device=None):
        self.playing = False

    def play(self, filepath: str, loop: bool = True):
        self.playing = True
        print(f"[DEBUG] Tocando áudio simulado: {filepath} (loop={loop})")
        if loop:
            threading.Thread(target=self._simulate_loop, daemon=True).start()

    def _simulate_loop(self):
        while self.playing:
            time.sleep(2)
            print("[DEBUG] Áudio tocando...")

    def stop(self):
        if self.playing:
            print("[DEBUG] Parando áudio simulado")
        self.playing = False

    @staticmethod
    def set_volume(percent: int):
        print(f"[DEBUG] Volume ajustado para {percent}% (simulado)")
