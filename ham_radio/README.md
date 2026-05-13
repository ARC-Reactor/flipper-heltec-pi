# Ham Radio AI Tools

Two tools for integrating Claude AI into your ham radio shack.

| Tool | Interface | Best for |
|---|---|---|
| [`ham_radio_assistant.html`](ham_radio_assistant.html) | Browser | Quick voice Q&A, no installation |
| [`ham_radio_pipeline.py`](ham_radio_pipeline.py) | Python CLI | Tapping radio audio, QSO transcription, digital mode feeds |

---

## `ham_radio_assistant.html` — Browser Voice Assistant

A self-contained web app. Open in Chrome or Edge, enter your Anthropic API key, and talk hands-free. No server or installation required.

**Features:**
- Push-to-talk button or hold **Spacebar** to transmit
- Web Speech API transcription → Claude (`claude-sonnet-4-6`) → browser TTS readback
- Real-time waveform and S-meter visualization
- Configurable system prompt (station context, operator callsign, band plan, etc.)
- QSO log with timestamped export

**Usage:**
1. Open `ham_radio_assistant.html` in Chrome or Edge
2. Enter your Anthropic API key and click **CONNECT**
3. Hold the PTT button (or Spacebar) and speak — Claude responds in text and audio

> API key is held in memory only and sent directly to `api.anthropic.com`. Nothing is stored locally.

---

## `ham_radio_pipeline.py` — Python Audio Pipeline

Taps your radio's audio output for full local Whisper transcription and Claude analysis. Runs on Linux, macOS, or Windows (including Raspberry Pi).

### Installation

```bash
pip install -r requirements.txt
# Optional: GPU-accelerated Whisper (faster on noisy radio audio)
pip install torch  # use your CUDA build URL
```

### Environment

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Interactive | `python ham_radio_pipeline.py` | PTT/VOX Q&A with Claude |
| Transcribe | `python ham_radio_pipeline.py --mode transcribe` | Log all QSO audio |
| Pipe | `python ham_radio_pipeline.py --mode pipe` | fldigi / WSJT-X digital decode feed |

### Common options

```bash
# List audio input devices — find your rig's USB audio interface
python ham_radio_pipeline.py --list-devices

# Use a specific audio device (replace 3 with your device index)
python ham_radio_pipeline.py --device 3

# VOX mode: starts recording automatically on audio level
python ham_radio_pipeline.py --vox

# Larger Whisper model for better accuracy on noisy / weak signals
python ham_radio_pipeline.py --whisper-model small

# Disable TTS readback
python ham_radio_pipeline.py --no-tts
```

### Piping from fldigi

In fldigi: **Configure → Misc → NBEMS → Enable ARQ** or use the macro `<EXEC>` to pipe output. Alternatively redirect the fldigi log:

```bash
tail -f ~/.fldigi/logs/logbook.adif | python ham_radio_pipeline.py --mode pipe
```

### Piping from WSJT-X / JS8Call

```bash
tail -f ~/WSJT-X/wsjtx_log.adi | python ham_radio_pipeline.py --mode pipe
```

---

## Hardware Setup

```
[Radio audio out] ──► [USB audio interface / sound card]
                                    │
                              [PC / Raspberry Pi]
                                    │
                         ham_radio_pipeline.py
                                    │
                         [Whisper STT] → [Claude API]
                                    │
                              [TTS readback]
                              [QSO log file]
```

A **Tigertronics SignaLink USB** or **DigiRig Mobile** works well as the audio interface between rig and PC.

---

## Log Format

Both tools write a JSONL log (`qso_log.jsonl`):

```json
{"timestamp": "2025-01-15T14:32:11Z", "role": "user", "text": "What's the current solar flux?"}
{"timestamp": "2025-01-15T14:32:13Z", "role": "assistant", "text": "Solar flux is around 145 SFU today..."}
```

Export to readable text: `python ham_radio_pipeline.py` then type `export`.

---

73 de ARC-Reactor
