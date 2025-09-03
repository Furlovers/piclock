import subprocess
import logging
from datetime import datetime

class RTC:
    @staticmethod
    def hwclock_to_system():
        """
        Copia a hora do RTC para o sistema.
        Equivalente a: sudo hwclock -s
        """
        try:
            subprocess.run(["sudo", "hwclock", "-s"], check=True)
            logging.info("Hora do RTC carregada para o sistema.")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao sincronizar do RTC para o sistema: {e}")
            return False

    @staticmethod
    def system_to_hwclock():
        """
        Copia a hora atual do sistema para o RTC.
        Equivalente a: sudo hwclock -w
        """
        try:
            subprocess.run(["sudo", "hwclock", "-w"], check=True)
            logging.info("Hora do sistema gravada no RTC.")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao sincronizar do sistema para o RTC: {e}")
            return False

    @staticmethod
    def read_time():
        """
        Lê a hora do RTC.
        Equivalente a: sudo hwclock -r
        """
        try:
            result = subprocess.run(
                ["sudo", "hwclock", "-r"], check=True, capture_output=True, text=True
            )
            logging.info(f"RTC: {result.stdout.strip()}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Erro ao ler o RTC: {e}")
            return None

    @staticmethod
    def get_datetime():
        """
        Retorna a hora do sistema como objeto datetime.
        """
        return datetime.now()
