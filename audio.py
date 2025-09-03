from gpiozero import Buzzer
from signal import pause
import threading
import time

BUZZER_PIN = 23  # GPIO0 (BCM numbering)

class AudioPlayer:
    def __init__(self):
        self.buzzer = Buzzer(BUZZER_PIN)
        self.playing = False
        self.thread = None

    def play(self, filepath=None, loop=True):
        self.stop()
        self.playing = True
        self.thread = threading.Thread(target=self._buzz_loop, daemon=True)
        self.thread.start()

    def _buzz_loop(self):
        while self.playing:
            self.buzzer.on()
            time.sleep(0.5)
            self.buzzer.off()
            time.sleep(0.5)

    def stop(self):
        self.playing = False
        if self.thread:
            self.thread.join(timeout=0.1)
        self.buzzer.off()

    @staticmethod
    def set_volume(percent: int):
        # Não aplicável para buzzer direto
        pass
