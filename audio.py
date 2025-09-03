import os
import subprocess

class AudioPlayer:
    def __init__(self, device=None):
        self.proc = None
        self.device = device  # Ex.: 'hw:1,0' se for USB; normalmente None já funciona

    def play(self, filepath: str, loop: bool = True):
        """Toca um arquivo de áudio (MP3/WAV)."""
        self.stop()
        if not os.path.exists(filepath):
            raise FileNotFoundError(filepath)
        # Usa mpg123 para MP3 (loop se necessário)
        cmd = ["mpg123", "-q"]
        if self.device:
            cmd += ["-a", self.device]
        if loop:
            cmd += ["--loop", "-1"]
        cmd += [filepath]
        self.proc = subprocess.Popen(cmd)

    def stop(self):
        """Para a reprodução."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    @staticmethod
    def set_volume(percent: int):
        """Ajusta o volume de saída (0 a 100%)."""
        p = max(0, min(100, int(percent)))
        subprocess.run(["amixer", "set", "Master", f"{p}%"], stdout=subprocess.DEVNULL)
