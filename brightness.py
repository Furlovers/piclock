from pathlib import Path

# Caminhos para a tela oficial do Raspberry Pi 7"
BRIGHTNESS_PATH = Path("/sys/class/backlight/rpi_backlight/brightness")
MAX_PATH = Path("/sys/class/backlight/rpi_backlight/max_brightness")

class Backlight:
    @staticmethod
    def get_max():
        """Obtém o valor máximo de brilho suportado pela tela."""
        try:
            return int(MAX_PATH.read_text().strip())
        except Exception:
            return 255  # fallback genérico

    @staticmethod
    def set(value: int):
        """Define o brilho da tela (0 até max)."""
        try:
            maxv = Backlight.get_max()
            v = max(0, min(maxv, int(value)))
            BRIGHTNESS_PATH.write_text(str(v))
            return True
        except Exception:
            return False
