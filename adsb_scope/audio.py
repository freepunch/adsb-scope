"""Audio playback and tone generation, shared by the splash and the alerts.

Playback goes through the OS's own player in a subprocess rather than
QtMultimedia: QSoundEffect hard-crashes the whole process on a machine
with no sound server, and a crash is something you cannot catch.
"""
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Optional

RATE = 22050


def player_cmd() -> Optional[list[str]]:
    """The command to play a WAV file, or None if nothing is available."""
    if sys.platform == "darwin" and shutil.which("afplay"):
        return ["afplay"]
    for cmd in ("paplay", "aplay", "pw-play"):
        if shutil.which(cmd):
            return [cmd] + (["-q"] if cmd == "aplay" else [])
    return None


def play_wav(path: Path) -> bool:
    """Fire and forget. Returns False if no player could be started."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.PlaySound(str(path),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        cmd = player_cmd()
        if not cmd:
            return False
        subprocess.Popen(cmd + [str(path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _square(freq: float, i: int) -> float:
    """Square wave sample: the voice of a 2600, not a sine."""
    return 1.0 if (i * freq / RATE) % 1.0 < 0.5 else -1.0


def make_chiptune(path: Path, notes: list[tuple[float, int]],
                  amplitude: int = 9000) -> Path:
    """Render a sequence of (frequency Hz, duration ms) as a square-wave WAV.

    A short attack and a decay tail are applied per note so the chip voice
    does not click between steps. Frequency 0 is a rest.
    """
    frames = bytearray()
    for freq, ms in notes:
        n = int(RATE * ms / 1000)
        for i in range(n):
            if freq <= 0:
                frames += struct.pack("<h", 0)
                continue
            # linear attack over 2 ms, decay across the back half
            attack = min(1.0, i / (RATE * 0.002))
            decay = min(1.0, (n - i) / (n * 0.5)) if n else 1.0
            frames += struct.pack(
                "<h", int(amplitude * _square(freq, i) * attack * decay))
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return path


# Rising A-major arpeggio into a held octave: eight notes, about 1.1 s,
# which lands under the colour bars and the first letters of the logo.
STARTUP_NOTES = [
    (220.0, 70),    # A3
    (277.2, 70),    # C#4
    (329.6, 70),    # E4
    (440.0, 70),    # A4
    (554.4, 70),    # C#5
    (659.3, 70),    # E5
    (0.0, 40),      # beat of silence
    (880.0, 420),   # A5, held
]


def startup_sound_path() -> Optional[Path]:
    """Render the boot chime to a temp file. None if rendering fails."""
    try:
        path = Path(tempfile.gettempdir()) / "airaware_startup.wav"
        if not path.exists():
            make_chiptune(path, STARTUP_NOTES)
        return path
    except Exception:
        return None


def play_startup_sound() -> bool:
    path = startup_sound_path()
    return play_wav(path) if path else False
