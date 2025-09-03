import RPi.GPIO as GPIO
import threading
import time

BUZZER_PIN = 18  # PWM
GND_PIN = 34     # ligado ao GND do buzzer

class AudioPlayer:
    def __init__(self):
        self.playing = False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUZZER_PIN, GPIO.OUT)
        GPIO.setup(GND_PIN, GPIO.OUT)
        GPIO.output(GND_PIN, GPIO.LOW)
        self.pwm = GPIO.PWM(BUZZER_PIN, 1000)  # frequência inicial 1kHz
        self.thread = None

    def play(self, filepath=None, loop=True):
        self.stop()
        self.playing = True
        self.thread = threading.Thread(target=self._buzz_loop, daemon=True)
        self.thread.start()

    def _buzz_loop(self):
        self.pwm.start(50)  # 50% duty cycle
        while self.playing:
            time.sleep(0.5)
            self.pwm.ChangeFrequency(1500)
            time.sleep(0.5)
            self.pwm.ChangeFrequency(1000)
        self.pwm.stop()
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    def stop(self):
        self.playing = False
        if self.thread:
            self.thread.join(timeout=0.1)
        self.pwm.stop()
        GPIO.output(BUZZER_PIN, GPIO.LOW)

    @staticmethod
    def set_volume(percent: int):
        # volume não é aplicável em buzzer
        pass
