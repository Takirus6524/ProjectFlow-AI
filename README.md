 # ProjectFlow-AI

 ## Description

 ProjectFlow AI is an intelligent programming companion that generates unique, personalized project ideas tailored to your skills, interests, and goals. Unlike traditional project lists, our app uses AI to create fresh, innovative programming challenges that evolve with you.

Tkinter GUI that generates programming project ideas via AI. Backends supported: OpenAI, Mistral, Google Gemini.

## Requirements

- Python 3.8+
- `requests` (installed via `requirements.txt`)
- `tkinter` (built-in on most platforms; install `python3-tk` if missing)

Optional (not required):
- `transformers`, `torch` (listed but unused by default)

## Setup API Keys (no code changes needed)

Set environment variables (or use a `.env` that your shell loads):
- `OPENAI_API_KEY` for OpenAI
- `MISTRAL_API_KEY` for Mistral
- `GEMINI_API_KEY` for Google Gemini

Example (bash):
```bash
export OPENAI_API_KEY=your_openai_key
export MISTRAL_API_KEY=your_mistral_key
export GEMINI_API_KEY=your_gemini_key
```
Then restart the app so it picks up the variables.

## Run

```bash
python3 main.py
```

The default backend is Mistral. You can switch backends from the dropdown in the GUI; a backend is enabled only when its env var is set.

## Features

- 3 tabs: Generate, History, Settings
- Backend selector with status indicators
- Exports: JSON, Markdown, Text
- Project details include tech stack, features, learning outcomes, duration, difficulty, and more
- History with timestamps and backend used

## Troubleshooting

- If you see "API key not configured", set the env var for that backend and restart.
- If OpenAI/Gemini hit rate limits (429), the app will retry briefly and may fall back to Mistral if available.
- Ensure internet connectivity for cloud backends.
