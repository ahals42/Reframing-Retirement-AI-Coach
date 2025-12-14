# Reframing Retirement Coach

Conversational CLI agent that embodies a non-clinical, autonomy-supportive physical-activity coach for newly retired adults. It wraps the OpenAI Chat Completions API with a carefully crafted system prompt and lightweight heuristics to keep track of inferred user context (stage, barriers, preferred activities, time available).

## Setup

1. **Python**
   - Requires Python 3.10+.
2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment variables**
   - Copy `.env.example` to `.env` (or create `.env`) with:
     ```
     OPEN_API_KEY=sk-...
     OPENAI_MODEL=gpt-3.5-turbo   # optional override
     ```
   - The application uses `python-dotenv` to load this file automatically.

## Usage

Run the CLI:

```bash
python main.py
```

Type messages to converse with the coach. `exit`/`quit` (or Ctrl+C/D) cleanly stop the session.

## Project Layout

- `main.py` – CLI entry point, conversation loop, OpenAI integration, and heuristic state inference.
- `prompts/` – houses the base prompt and helper to inject inferred variables.
- `requirements.txt` – Python dependencies.
- `.env` – local secrets (never commit real keys).

## Notes

- The agent intentionally avoids clinical/diagnostic guidance and keeps conversations autonomy-supportive.
- `main.py` currently uses the Chat Completions endpoint via `openai>=1.0.0`. Update `OPENAI_MODEL` if you prefer another compatible model (e.g., `gpt-4o-mini`).

