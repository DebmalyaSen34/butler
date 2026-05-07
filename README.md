# Jarvis AI Assistant

A local, voice-activated AI assistant built with a modular architecture. This project integrates state-of-the-art local models for Wake Word detection, Speech-to-Text (STT), Large Language Models (LLM), and Text-to-Speech (TTS), complemented by dynamic tool-calling capabilities (like web search and file creation).

## Features

- **Wake Word Detection:** Always-on listening using `openwakeword`. Say **"Jarvis"** to wake the assistant.
- **Speech-to-Text (STT):** High-performance, local STT powered by `mlx_whisper` (optimized for Apple Silicon).
- **Brain / LLM Engine:** Connects to a local `llama.cpp` server (defaulting to Gemma variants). It maintains conversation history for context-aware responses.
- **Text-to-Speech (TTS):** Natural and expressive voice synthesis via the `kokoro` TTS engine.
- **Tool Calling:** The assistant can autonomously use tools to fulfill requests:
  - **Web Search:** Searches the internet using a local [SearxNG](https://github.com/searxng/searxng) instance and summarizes the results.
  - **File Operations:** Can create files dynamically on your computer.
- **Rich Terminal UX:** Colorful, intuitive terminal logging using `rich`.
- **Audio Feedback:** macOS native audio cues (`afplay`) to indicate when Jarvis wakes up and goes back to sleep.

## Architecture & Directory Structure

```text
jarvis/
├── main.py                # Main entry point: coordinates the STT, LLM, TTS, and wake word engines
├── requirements.txt       # Python dependencies
├── config/
│   └── settings.py        # Configuration files (API URLs, prompt templates)
├── core/
│   └── llm.py             # LLM orchestration, conversation history, and tool feedback loops
├── engine/
│   ├── stt.py             # Speech-to-Text handler (MLX Whisper)
│   ├── tts.py             # Text-to-Speech handler (Kokoro)
│   └── wake_word.py       # Wake word detection logic
├── tools/
│   ├── registry.py        # Maps tool configurations and provides tools prompt context
│   ├── web_search.py      # SearxNG web search tool implementation
│   └── file_ops.py        # File creation tool implementation
└── utils/
    ├── audio.py           # Handles macOS native audio cues (`afplay`)
    └── parser.py          # Robust JSON parsing for LLM tool execution strings
```

## Prerequisites

Because STT natively uses `mlx_whisper` and audio cues run via `afplay`, this project is highly optimized for **macOS (Apple Silicon)**.

You will also need two local services running in the background for the assistant to fully function:
1. **Llama.cpp Server:** An LLM server for the brain. (Default: `http://127.0.0.1:8080`)
2. **SearxNG Server:** A privacy-respecting metasearch engine for the web search tool. (Default: `http://127.0.0.1:8081`)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd jarvis
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure you have the proper system packages for `SpeechRecognition`, `mlx_whisper`, `openwakeword`, and `kokoro`.)*

## Services Setup

### 1. Start the LLM (llama.cpp)
Run a compatible instruction-tuned model (e.g., Gemma 2 or Llama 3) via the `llama-server` binary on port `8080`:
```bash
./llama-server -m /path/to/your/model.gguf -c 4096 --port 8080
```

### 2. Start SearxNG (Docker)
To enable the web search capability, run a local SearxNG container mapped to port `8081`:
```bash
docker run -d -p 8081:8080 \
  -e "BASE_URL=http://localhost:8081/" \
  searxng/searxng
```

## Usage

1. Ensure your microphone is connected and authorized.
2. Run the main script:
   ```bash
   python main.py
   ```
3. Await the ready prompt in the terminal: `Pipeline Ready. Say 'Jarvis' to wake me.`
4. Say **"Jarvis"**. Once the wake chime plays, specify your query or command (e.g., *"What is the latest news on AI?"* or *"Create a file named hello.txt that says hi"*).

## Customization

- **Voices:** In `main.py`, you can change `target_voice = "af_heart"` to any compatible Kokoro voice.
- **Wake Word:** By default, `openwakeword` loads the `jarvis` model. You can modify this in `main.py`.
- **System Prompts:** You can adjust the LLM structure and behavior via `config/settings.py` by editing the `PROMPT_TEMPLATE`.

## Logging and Troubleshooting

- The project uses `rich` for clean, colorful console logs.
- If the LLM generates improper tool-calling schema, `utils/parser.py` includes robust regex bounds to attempt self-correction. Watch the terminal output for instances where the agent skips a step due to JSON decoding issues.
