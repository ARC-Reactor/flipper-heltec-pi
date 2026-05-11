#!/usr/bin/env python3
"""
ham_radio_pipeline.py
─────────────────────────────────────────────────────────────────────────────
ARC-Reactor Ham Radio AI Pipeline
Captures audio from a radio's audio-out (or any sound card input),
transcribes it with OpenAI Whisper (local), and sends it to Claude.
Optionally speaks responses back via TTS.

Use Cases:
  1. QSO Transcription  — records and logs radio conversations
  2. Hands-free AI Q&A  — push-to-talk key triggers question to Claude
  3. Digital mode log feeding — pipe fldigi/WSJT-X text directly to Claude

Requirements:
  pip install anthropic openai-whisper pyaudio pyttsx3 numpy sounddevice

For GPU acceleration with Whisper:
  pip install torch  (CUDA version for your GPU)

Usage:
  python ham_radio_pipeline.py                     # Interactive PTT mode
  python ham_radio_pipeline.py --mode transcribe   # Continuous QSO transcription
  python ham_radio_pipeline.py --mode pipe         # Pipe text from stdin (fldigi etc.)
  python ham_radio_pipeline.py --list-devices      # Show audio input devices
"""

import os
import sys
import json
import time
import queue
import signal
import logging
import argparse
import threading
import tempfile
from datetime import datetime
from pathlib import Path

import numpy as np

# ── Optional imports (graceful degradation) ───────────────────────────────────
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False
    print("[WARN] sounddevice not installed — audio capture disabled")

try:
    import whisper
    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    print("[WARN] openai-whisper not installed — using browser STT fallback")

try:
    import pyttsx3
    HAS_TTS = True
except ImportError:
    HAS_TTS = False
    print("[WARN] pyttsx3 not installed — TTS disabled")

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[ERROR] anthropic not installed — run: pip install anthropic")
    sys.exit(1)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s  %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('ham-ai')

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "api_key": "",                  # Set ANTHROPIC_API_KEY env var or paste here
    "model": "claude-sonnet-4-20250514",
    "system_prompt": (
        "You are an AI assistant for a ham radio operator. "
        "Keep responses concise and radio-friendly. "
        "Use the phonetic alphabet when spelling callsigns (Alpha, Bravo, etc). "
        "Be helpful with propagation, band conditions, FCC regulations, "
        "antenna theory, operating procedures, contest rules, and SOTA/POTA."
    ),
    "whisper_model": "base",        # tiny | base | small | medium | large
    "sample_rate": 16000,           # Hz — Whisper expects 16 kHz
    "channels": 1,
    "chunk_seconds": 0.5,           # Audio buffer chunk size
    "silence_threshold": 0.01,      # RMS level below which audio is silence
    "silence_duration": 1.5,        # Seconds of silence before ending a segment
    "max_record_seconds": 30,       # Max single recording length
    "audio_device": None,           # None = default. Use --list-devices to find ID
    "tts_rate": 175,                # TTS words per minute
    "tts_voice_index": 0,           # Voice index for pyttsx3
    "log_file": "qso_log.jsonl",    # JSONL log of all transcripts + AI responses
    "vox_mode": False,              # VOX: auto-start on audio level (vs PTT key)
    "vox_threshold": 0.02,          # RMS threshold for VOX trigger
}


# ── QSO Logger ────────────────────────────────────────────────────────────────
class QSOLogger:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def write(self, role: str, text: str, metadata: dict | None = None):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "role": role,
            "text": text,
            **(metadata or {})
        }
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        return entry

    def export_txt(self, out_path: str | None = None):
        out = Path(out_path or self.filepath.stem + "_export.txt")
        with open(self.filepath) as f, open(out, 'w') as o:
            o.write(f"ARC-Reactor QSO Log — Exported {datetime.utcnow().isoformat()}Z\n")
            o.write("=" * 60 + "\n\n")
            for line in f:
                e = json.loads(line)
                o.write(f"[{e['timestamp']}] {e['role'].upper():12s} {e['text']}\n")
        log.info(f"Log exported to {out}")
        return out


# ── TTS Engine ────────────────────────────────────────────────────────────────
class TTSEngine:
    def __init__(self, rate: int = 175, voice_index: int = 0):
        self._engine = None
        self.rate = rate
        self.voice_index = voice_index
        if HAS_TTS:
            self._init()

    def _init(self):
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.rate)
            voices = self._engine.getProperty('voices')
            if voices and self.voice_index < len(voices):
                self._engine.setProperty('voice', voices[self.voice_index].id)
        except Exception as e:
            log.warning(f"TTS init failed: {e}")
            self._engine = None

    def speak(self, text: str):
        if not self._engine:
            print(f"[TTS] {text}")
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            log.warning(f"TTS speak error: {e}")


# ── Whisper Transcriber ───────────────────────────────────────────────────────
class WhisperTranscriber:
    def __init__(self, model_name: str = "base"):
        if not HAS_WHISPER:
            raise RuntimeError("openai-whisper is not installed")
        log.info(f"Loading Whisper model '{model_name}' ...")
        self.model = whisper.load_model(model_name)
        log.info("Whisper ready")

    def transcribe(self, audio_array: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe a numpy float32 audio array."""
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)
        # Whisper expects mono 16 kHz
        if sample_rate != 16000:
            import librosa
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
        result = self.model.transcribe(audio_array, fp16=False)
        return result["text"].strip()


# ── Audio Recorder ────────────────────────────────────────────────────────────
class AudioRecorder:
    def __init__(self, config: dict):
        self.config = config
        self.sample_rate = config["sample_rate"]
        self.channels = config["channels"]
        self.device = config["audio_device"]
        self.chunk = int(self.sample_rate * config["chunk_seconds"])
        self._recording = False
        self._buf: list[np.ndarray] = []

    @staticmethod
    def list_devices():
        if not HAS_SD:
            print("sounddevice not installed")
            return
        print("\nAvailable audio input devices:")
        print("-" * 50)
        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                print(f"  [{i:2d}]  {d['name']}  ({d['max_input_channels']}ch, {int(d['default_samplerate'])}Hz)")
        print()

    def record_ptt(self, max_seconds: int = 30) -> np.ndarray | None:
        """Record while user holds Enter, returns audio array."""
        if not HAS_SD:
            log.error("sounddevice not available")
            return None

        print("\n  >>> HOLD ENTER to transmit, release to stop <<<\n")
        import msvcrt  # Windows
        try:
            use_msvcrt = True
            msvcrt.getch  # test
        except AttributeError:
            use_msvcrt = False

        buf: list[np.ndarray] = []
        stop_event = threading.Event()

        def callback(indata, frames, time_info, status):
            buf.append(indata.copy().flatten())

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            device=self.device,
            blocksize=self.chunk,
            callback=callback
        )

        with stream:
            # Wait for Enter press
            input()
            stream.start() if not stream.active else None
            start = time.time()
            log.info("● Recording...")
            try:
                input()  # Wait for Enter release (second press)
            except (KeyboardInterrupt, EOFError):
                pass
            elapsed = time.time() - start
            log.info(f"■ Stopped ({elapsed:.1f}s)")

        return np.concatenate(buf) if buf else None

    def record_vox(
        self,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_seconds: int = 30
    ) -> np.ndarray | None:
        """VOX mode: starts recording on audio level, stops on silence."""
        if not HAS_SD:
            return None

        buf: list[np.ndarray] = []
        silent_chunks = 0
        required_silent = int(silence_duration / self.config["chunk_seconds"])
        max_chunks = int(max_seconds / self.config["chunk_seconds"])
        triggered = False
        q: queue.Queue = queue.Queue()

        def callback(indata, frames, time_info, status):
            q.put(indata.copy().flatten())

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32',
            device=self.device,
            blocksize=self.chunk,
            callback=callback
        ):
            log.info("VOX listening...")
            while len(buf) < max_chunks:
                chunk = q.get()
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                if not triggered:
                    if rms > self.config["vox_threshold"]:
                        triggered = True
                        log.info("● VOX triggered — recording")
                else:
                    buf.append(chunk)
                    if rms < silence_threshold:
                        silent_chunks += 1
                        if silent_chunks >= required_silent:
                            log.info(f"■ VOX silence detected — stopped ({len(buf) * self.config['chunk_seconds']:.1f}s)")
                            break
                    else:
                        silent_chunks = 0

        return np.concatenate(buf) if buf else None


# ── Claude Client ─────────────────────────────────────────────────────────────
class ClaudeClient:
    def __init__(self, api_key: str, model: str, system_prompt: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.history: list[dict] = []

    def ask(self, text: str) -> str:
        self.history.append({"role": "user", "content": text})
        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt,
            messages=self.history
        )
        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []
        log.info("Conversation history cleared")


# ── Modes ─────────────────────────────────────────────────────────────────────

def mode_interactive(config: dict):
    """PTT / VOX interactive Q&A with Claude."""
    api_key = config["api_key"] or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY env var or add it to config")
        sys.exit(1)

    whisper_tx = WhisperTranscriber(config["whisper_model"]) if HAS_WHISPER else None
    claude = ClaudeClient(api_key, config["model"], config["system_prompt"])
    tts = TTSEngine(config["tts_rate"], config["tts_voice_index"])
    recorder = AudioRecorder(config)
    qso_log = QSOLogger(config["log_file"])

    print("\n" + "═" * 60)
    print("  ARC-REACTOR HAM RADIO AI  —  INTERACTIVE MODE")
    print("  Commands: 'reset' clear history | 'export' save log | 'quit'")
    print("═" * 60 + "\n")

    while True:
        try:
            if config["vox_mode"] and HAS_SD:
                audio = recorder.record_vox(
                    config["silence_threshold"],
                    config["silence_duration"],
                    config["max_record_seconds"]
                )
                if audio is None:
                    continue
                text = whisper_tx.transcribe(audio, config["sample_rate"])
            elif HAS_SD and HAS_WHISPER:
                audio = recorder.record_ptt(config["max_record_seconds"])
                if audio is None:
                    continue
                log.info("Transcribing...")
                text = whisper_tx.transcribe(audio, config["sample_rate"])
            else:
                # Fallback: typed input
                text = input("\n[TYPE YOUR MESSAGE] > ").strip()

            if not text:
                continue

            cmd = text.lower().strip()
            if cmd in ("quit", "exit", "73"):
                print("73 de AI — logging off")
                break
            if cmd == "reset":
                claude.reset()
                continue
            if cmd == "export":
                qso_log.export_txt()
                continue

            print(f"\n  TX: {text}")
            qso_log.write("user", text)

            log.info("Asking Claude...")
            reply = claude.ask(text)

            print(f"  RX: {reply}\n")
            qso_log.write("assistant", reply)
            tts.speak(reply)

        except KeyboardInterrupt:
            print("\n\n73 — QSO ended")
            break


def mode_transcribe(config: dict):
    """Continuous QSO transcription mode — logs everything heard."""
    if not HAS_WHISPER or not HAS_SD:
        print("ERROR: whisper and sounddevice required for transcription mode")
        sys.exit(1)

    whisper_tx = WhisperTranscriber(config["whisper_model"])
    recorder = AudioRecorder(config)
    qso_log = QSOLogger(config["log_file"])

    print("\n" + "═" * 60)
    print("  ARC-REACTOR —  CONTINUOUS TRANSCRIPTION MODE")
    print("  Ctrl+C to stop and export log")
    print("═" * 60 + "\n")

    segments = 0
    try:
        while True:
            audio = recorder.record_vox(
                config["silence_threshold"],
                config["silence_duration"],
                config["max_record_seconds"]
            )
            if audio is None:
                continue
            text = whisper_tx.transcribe(audio, config["sample_rate"])
            if text:
                segments += 1
                ts = datetime.utcnow().strftime("%H:%M:%S")
                print(f"  [{ts}] {text}")
                qso_log.write("radio", text)
    except KeyboardInterrupt:
        print(f"\n\nTranscription ended — {segments} segments captured")
        qso_log.export_txt()


def mode_pipe(config: dict):
    """
    Read decoded digital mode text from stdin (e.g. fldigi pipe)
    and send to Claude for analysis/response.
    
    Usage:
      fldigi | python ham_radio_pipeline.py --mode pipe
      # or
      python ham_radio_pipeline.py --mode pipe < decoded_traffic.txt
    """
    api_key = config["api_key"] or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: Set ANTHROPIC_API_KEY env var")
        sys.exit(1)

    system = (
        config["system_prompt"] +
        "\n\nYou are receiving decoded digital mode ham radio traffic (FT8, RTTY, "
        "PSK31, JS8Call, etc.). Analyze the traffic, identify callsigns, "
        "summarize exchanges, flag anything interesting (DX, rare grids, emergencies)."
    )
    claude = ClaudeClient(api_key, config["model"], system)
    tts = TTSEngine(config["tts_rate"])
    qso_log = QSOLogger(config["log_file"])

    print("Piped digital mode input — reading from stdin...")
    buffer = []
    flush_interval = 10  # lines before sending to Claude

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            buffer.append(line)
            print(f"  >> {line}")
            qso_log.write("digital", line)

            if len(buffer) >= flush_interval:
                batch = "\n".join(buffer)
                buffer = []
                log.info("Analyzing batch with Claude...")
                analysis = claude.ask(f"Analyze this decoded traffic batch:\n\n{batch}")
                print(f"\n  [AI] {analysis}\n")
                qso_log.write("assistant", analysis)
                tts.speak(analysis)

    except KeyboardInterrupt:
        if buffer:
            analysis = claude.ask("\n".join(buffer))
            print(f"\n  [AI] {analysis}\n")
            qso_log.write("assistant", analysis)


# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ARC-Reactor Ham Radio AI Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--mode",
        choices=["interactive", "transcribe", "pipe"],
        default="interactive",
        help="Operating mode (default: interactive)"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit"
    )
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        help="Audio input device index (use --list-devices to find)"
    )
    parser.add_argument(
        "--whisper-model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Whisper model size (default: base)"
    )
    parser.add_argument(
        "--vox",
        action="store_true",
        help="Enable VOX mode (auto-start on audio level)"
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Disable text-to-speech readback"
    )
    parser.add_argument(
        "--log",
        default="qso_log.jsonl",
        help="Path to JSONL log file (default: qso_log.jsonl)"
    )
    args = parser.parse_args()

    if args.list_devices:
        AudioRecorder.list_devices()
        return

    config = dict(DEFAULT_CONFIG)
    if args.device is not None:
        config["audio_device"] = args.device
    config["whisper_model"] = args.whisper_model
    config["vox_mode"] = args.vox
    config["log_file"] = args.log
    if args.no_tts:
        globals()['HAS_TTS'] = False

    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    if args.mode == "interactive":
        mode_interactive(config)
    elif args.mode == "transcribe":
        mode_transcribe(config)
    elif args.mode == "pipe":
        mode_pipe(config)


if __name__ == "__main__":
    main()
