from datetime import datetime

class RTC:
    @staticmethod
    def hwclock_to_system():
        print("[DEBUG] Sincronizando hora do RTC → Sistema (simulado)")
        return True

    @staticmethod
    def system_to_hwclock():
        print("[DEBUG] Sincronizando hora do Sistema → RTC (simulado)")
        return True

    @staticmethod
    def read_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_datetime():
        return datetime.now()
