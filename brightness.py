class Backlight:
    @staticmethod
    def get_max():
        return 255

    @staticmethod
    def set(value: int):
        print(f"[DEBUG] Brilho simulado ajustado para {value}")
        return True
