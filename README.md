# Listing Doctor

A Streamlit app that helps independent short-term rental hosts get more bookings. It scores a listing, spots extras in the photos that the host forgot to list, rewrites the listing in the host's chosen tone, and drafts replies to guest questions using only the host's own facts.

OIM 3641 · Declan Hehir · Charles Zhang · Alexander Kozin

## How to build and run

You need Python 3.10 or newer ([python.org/downloads](https://www.python.org/downloads/)). On Mac, type `python3` where it says `python`.

```bash
python run.py setup   # once: creates .venv and installs everything (about 2 minutes)
python run.py test    # runs the 5 tests
python run.py app     # opens the app at http://localhost:8501 (Ctrl+C to stop)
```

`python run.py` on its own prints the full guide. `python run.py check` shows what's installed and what to run next.

**Live AI (optional):** `python run.py key` saves your Gemini API key to `.streamlit/secrets.toml` (git ignores this file). Get a free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Without a key the app runs in **demo mode**: the sample listing works fully offline. Optional: set `GEMINI_MODEL` to change the model (default `gemini-2.5-flash`).

GitHub runs the tests on every push (`.github/workflows/tests.yml`).

## Flow

1. **Your listing**: load Maria's Newport sample or paste your own text and photos.
2. **Diagnose**: score title, description and amenities (0 to 10) and list issues. Gemini also looks at the photos and lists features that aren't in the listing. The host confirms which are real.
3. **Rewrite**: pick a tone, get a new title, description and amenities list, plus a new score. Type a change ("mention the 5-minute walk") to refine. Download as text.
4. **Guest replies**: answers come only from the listing and house facts. If the answer isn't there, the reply says the host will follow up and the message is flagged.

## Code map

| File | Layer | What it does |
|---|---|---|
| `app.py` | UI | Streamlit screens, session state, error handling |
| `core/models.py` | Data | `Listing`, `Photo`; Pydantic schemas `Diagnosis`, `Rewrite`, `GuestReply` (also Gemini's JSON response schemas) |
| `core/prompts.py` | AI | Scoring rubric and prompt templates |
| `core/ai.py` | AI | `GeminiService` (live) and `DemoService` (offline) with the same three methods: `diagnose`, `rewrite`, `answer` |
| `data/` | Data | Sample listing JSON and photos |
| `tests/test_core.py` | Tests | Unit tests plus a full click-through with Streamlit's `AppTest` |
| `run.py` | Tooling | Setup, test, run and API-key commands with built-in help |

## Out of scope for the MVP

Airbnb link import, host account connection and auto-publish; vector database / LlamaIndex RAG (one listing fits in a single prompt); saved history (SQLite); performance dashboard; pricing; other platforms.
