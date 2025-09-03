import RPi.GPIO as GPIO
import time
import threading

class GpioButtons:
    def __init__(self, snooze_pin=17, stop_pin=27, callback=None):
        """
        snooze_pin: GPIO para soneca
        stop_pin: GPIO para parar alarme
        callback: função chamada quando botão é pressionado
                  callback(evento: str) -> None
                  evento pode ser "snooze" ou "stop"
        """
        self.snooze_pin = snooze_pin
        self.stop_pin = stop_pin
        self.callback = callback
        self.running = False
        self.thread = None

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.snooze_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.stop_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def _loop(self):
        while self.running:
            if GPIO.input(self.snooze_pin) == GPIO.LOW:
                if self.callback:
                    self.callback("snooze")
                time.sleep(0.5)  # debounce
            if GPIO.input(self.stop_pin) == GPIO.LOW:
                if self.callback:
                    self.callback("stop")
                time.sleep(0.5)  # debounce
            time.sleep(0.05)

    def start(self):
        """Inicia monitoramento dos botões em thread separada."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Para monitoramento e limpa GPIO."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        GPIO.cleanup()
