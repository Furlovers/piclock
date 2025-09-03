import RPi.GPIO as GPIO
import threading
import time

BUZZER_PIN = 6  # GPIO6

class AudioPlayer:
    def __init__(self):
        self.playing = False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
        self.thread = None

    def play(self, filepath=None, loop=True):
        """Dispara o buzzer (ignora filepath)"""
        self.stop()
        self.playing = True
        self.thread = threading.Thread(target=self._buzz_loop, daemon=True)
        self.thread.start()

    def _buzz_loop(self):
        while self.playing:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.5)  # ligado 0.5s
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(0.5)  # desligado 0.5s

    def stop(self):
        self.playing = False
        if self.thread:
            self.thread.join(timeout=0.1)
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    @staticmethod
    def set_volume(percent: int):
        # volume não é aplicável para buzzer direto
        pass
