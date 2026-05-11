# ARC-Reactor Ham Radio AI Tools

Two tools for integrating AI assistance into your ham radio shack.

---

## 1. `ham_radio_assistant.html` — Browser Voice Assistant

A self-contained web app. Open in Chrome or Edge, enter your Anthropic API key, and talk hands-free.

**Features:**
- Push-to-talk button (or hold **Spacebar**) triggers Web Speech API
- Transcribed speech sent to Claude (`claude-sonnet-4-20250514`)
- Responses read back via browser TTS
- Real-time waveform + S-meter visualization
- Configurable system prompt (station context, operator callsign, etc.)
- QSO log with timestamp export

**Usage:**
1. Open `ham_radio_assistant.html` in Chrome or Edge
2. Enter your Anthropic API key and click **CONNECT**
3. Hold the PTT button (or Spacebar) and speak
4. Claude responds in text and audio

> No server required. API key is held in memory only and sent directly to `api.anthropic.com`.

---

## 2. `ham_radio_pipeline.py` — Python Audio Pipeline

Taps your radio's audio output for full Whisper-based transcription and Claude analysis.

### Installation

```bash
pip install anthropic openai-whisper sounddevice pyttsx3 numpy
# For GPU acceleration:
pip install torch  # CUDA build for your GPU
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

### Common Options

```bash
# List audio devices (find your radio's USB audio interface)
python ham_radio_pipeline.py --list-devices

# Use a specific device (e.g. your rig's USB audio out)
python ham_radio_pipeline.py --device 3

# VOX mode (auto-starts on audio level, no PTT needed)
python ham_radio_pipeline.py --vox

# Larger Whisper model for better accuracy on noisy radio audio
python ham_radio_pipeline.py --whisper-model small

# Pipe fldigi decoded text to Claude
fldigi-output | python ham_radio_pipeline.py --mode pipe
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
