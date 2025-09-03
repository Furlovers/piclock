class GpioButtons:
    def __init__(self, snooze_pin=17, stop_pin=27, callback=None):
        self.callback = callback

    def start(self):
        print("[DEBUG] GPIO Buttons mock: iniciado (use teclado para simular)")

    def stop(self):
        print("[DEBUG] GPIO Buttons mock: parado")

    # Você pode simular chamando isso no terminal
    def simulate_press(self, event):
        if self.callback:
            self.callback(event)
