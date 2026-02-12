# Voice Interview Assistant

A real-time voice interview assistant that answers questions based on a local knowledge base, speaks via ElevenLabs TTS in a cloned voice, and runs as a streaming voice agent.

## Features

- **Knowledge-grounded responses** — answers only from prepared Q&A and guide documents
- **Source citations** — every response includes file + section references
- **Streaming pipeline** — STT → LLM → TTS with low latency
- **Voice Activity Detection** — energy-based VAD with auto-calibration
- **Barge-in support** — interrupt the agent mid-speech by talking
- **Multiple modes** — voice (mic+speakers), text (CLI), web (browser)
- **Pluggable transports** — local audio, with stubs for Daily.co and LiveKit
- **Evaluation harness** — automated testing of response quality

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

For local STT (Whisper), also install:
```bash
pip install faster-whisper
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys:
- `LLM_API_KEY` — OpenAI API key (or compatible provider)
- `ELEVENLABS_API_KEY` — ElevenLabs API key (for voice output)
- `ELEVENLABS_VOICE_ID` — your cloned voice ID

Optional:
- `DEEPGRAM_API_KEY` — for streaming STT (alternative to Whisper)

### 3. Run

```bash
# Text mode (no audio hardware needed)
make dev
# or: python main.py --mode text

# Voice mode (requires mic + speakers)
make run
# or: python main.py --mode voice

# Web interface
make web
# or: python main.py --mode web
```

### 4. Run tests

```bash
make test
```

### 5. Run evaluation

```bash
make eval
# or: python -m eval.run
```

## Project Structure

```
├── main.py                  # Entry point (CLI)
├── src/
│   ├── config.py            # Settings from environment
│   ├── loop.py              # Voice and text interaction loops
│   ├── knowledge/
│   │   ├── loader.py        # Load FAQ, markdown, text files
│   │   ├── chunker.py       # Split documents into chunks
│   │   └── retriever.py     # BM25 retrieval with scoring
│   ├── agent/
│   │   ├── policy.py        # System prompt and conversation rules
│   │   └── agent.py         # Main agent (retrieval + LLM)
│   ├── llm/
│   │   ├── base.py          # Abstract LLM interface
│   │   └── openai_client.py # OpenAI streaming implementation
│   ├── tts/
│   │   ├── base.py          # Abstract TTS interface
│   │   └── elevenlabs_tts.py# ElevenLabs streaming TTS
│   ├── stt/
│   │   ├── base.py          # Abstract STT interface
│   │   ├── whisper_stt.py   # Local Whisper STT
│   │   └── deepgram_stt.py  # Deepgram streaming STT
│   ├── audio/
│   │   ├── vad.py           # Voice Activity Detection
│   │   ├── player.py        # Audio playback with barge-in
│   │   └── recorder.py      # Microphone capture
│   └── transport/
│       ├── base.py          # Abstract transport interface
│       ├── local.py         # Local mic+speakers
│       ├── daily_stub.py    # Daily.co stub
│       └── livekit_stub.py  # LiveKit stub
├── knowledge/               # Knowledge base files
│   ├── faq.json             # Structured Q&A
│   ├── guide.md             # Interview guide
│   └── company-culture.txt  # Company info
├── eval/
│   ├── run.py               # Evaluation harness
│   └── questions.json       # Test questions
├── tests/                   # Unit tests
└── web/
    └── index.html           # Minimal web interface
```

## Knowledge Base Format

### FAQ JSON (`knowledge/faq.json`)
```json
[
  {
    "q": "Question text",
    "a": "Answer text",
    "tags": ["tag1", "tag2"]
  }
]
```

### Markdown (`knowledge/*.md`)
Split by headings into chunks. Each section becomes a retrievable chunk.

### Plain text (`knowledge/*.txt`)
Split by paragraphs.

## Adding a Transport Adapter

Implement `src/transport/base.TransportAdapter`:

```python
class MyTransport(TransportAdapter):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def read_audio_frames(self) -> AsyncIterator[bytes]: ...
    async def write_audio(self, data: bytes) -> None: ...
    async def write_audio_stream(self, audio_iter: AsyncIterator[bytes]) -> None: ...
    def stop_playback(self) -> None: ...
    def is_playing(self) -> bool: ...
```

## Security Notes

- API keys are loaded from environment variables only — never committed
- Audio is processed in memory — not stored to disk by default
- WebSocket connections are unencrypted in development; use TLS in production

## Latency Metrics

The agent logs timing at each stage:
- **Retrieval time** — BM25 lookup over knowledge chunks
- **LLM TTFT** — time to first token from the language model
- **Total turn time** — from end of speech to end of response playback

## Roadmap

- [ ] Daily.co transport adapter
- [ ] LiveKit transport adapter
- [ ] Microsoft Teams integration
- [ ] Embedding-based retrieval (upgrade from BM25)
- [ ] Multi-language support
- [ ] Conversation analytics dashboard
