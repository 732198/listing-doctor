"""Listing Doctor launcher: one script to set up, test and run the app.

Works on Mac, Windows and Linux. Run it with no arguments to see the guide:

    python run.py            show this guide
    python run.py setup      create .venv and install everything (run once)
    python run.py check      show what's ready and what's missing
    python run.py test       run the automated tests
    python run.py app        start the app in your browser
    python run.py key        save your Gemini API key (optional, for live AI)

On Mac, use python3 if python isn't found.
"""
from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SECRETS = ROOT / ".streamlit" / "secrets.toml"
MIN_PY = (3, 10)

GUIDE = f"""
Listing Doctor: how to build and run
====================================

First time (about 2 minutes):
  1. python run.py setup     creates a virtual environment in .venv and installs
                             Streamlit, the Gemini SDK, Pydantic and pytest
  2. python run.py test      runs 5 tests, including a full click-through
  3. python run.py app       opens the app at http://localhost:8501

After that, only step 3. Stop the app with Ctrl+C in this window.

Live AI (optional):
  python run.py key          saves your Gemini API key to .streamlit/secrets.toml
  Get a free key at https://aistudio.google.com/apikey
  Without a key the app runs in demo mode: the sample listing works fully offline.

Something wrong?
  python run.py check        lists what's installed, what's missing and what to run next

Project layout:
  app.py            UI layer (Streamlit screens)
  core/ai.py        AI layer: GeminiService (live) and DemoService (offline)
  core/prompts.py   scoring rubric and prompt templates
  core/models.py    data layer: Listing and the schemas Gemini must fill
  data/             sample listing and photos
  tests/            automated tests

Using {sys.executable} (Python {sys.version.split()[0]}).
"""


def say(msg: str) -> None:
    print(f"\n>> {msg}", flush=True)


def fail(msg: str, fix: str) -> None:
    print(f"\n!! {msg}\n   Fix: {fix}\n", flush=True)
    sys.exit(1)


def need_python() -> None:
    if sys.version_info < MIN_PY:
        fail(
            f"Python {sys.version.split()[0]} is too old; Listing Doctor needs {MIN_PY[0]}.{MIN_PY[1]} or newer.",
            "install a newer Python from https://www.python.org/downloads/ and run this again.",
        )


def need_venv() -> None:
    if not PY.exists():
        fail("The project isn't set up yet.", "run:  python run.py setup")


def run(cmd: list[str]) -> int:
    print("   $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


# ---------------------------------------------------------------- commands

def setup() -> None:
    need_python()
    if PY.exists():
        say("Virtual environment already exists in .venv; updating packages.")
    else:
        say("Step 1 of 2: creating a virtual environment in .venv")
        venv.EnvBuilder(with_pip=True).create(VENV)
    say("Step 2 of 2: installing packages (Streamlit, google-genai, Pydantic, pytest)")
    if run([str(PY), "-m", "pip", "install", "--upgrade", "pip", "-q"]) != 0:
        fail("Couldn't upgrade pip.", "check your internet connection and run setup again.")
    if run([str(PY), "-m", "pip", "install", "-q", "-r", "requirements.txt", "-r", "requirements-dev.txt"]) != 0:
        fail("Package install failed.", "check your internet connection, then run:  python run.py setup")
    say("Setup complete. Next:  python run.py test   then   python run.py app")


def check() -> None:
    def line(ok: bool, label: str, hint: str = "") -> None:
        print(f"   [{'ok' if ok else '--'}] {label}" + (f"   ->  {hint}" if hint and not ok else ""))

    say("Listing Doctor status")
    line(sys.version_info >= MIN_PY, f"Python {sys.version.split()[0]} (needs 3.10+)",
         "install Python 3.10+ from python.org")
    line(PY.exists(), "Virtual environment (.venv)", "python run.py setup")
    if PY.exists():
        for pkg in ("streamlit", "google.genai", "pydantic", "pytest"):
            ok = subprocess.call([str(PY), "-c", f"import {pkg}"], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
            line(ok, f"Package: {pkg}", "python run.py setup")
    has_key = bool(os.getenv("GEMINI_API_KEY")) or (SECRETS.exists() and "GEMINI_API_KEY" in SECRETS.read_text())
    line(has_key, "Gemini API key (optional)", "python run.py key   (or keep using demo mode)")
    print(f"\n   Model: {os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}  (change with the GEMINI_MODEL env var)")
    print("   Mode when the app starts: " + ("live Gemini" if has_key else "demo mode (offline)"))


def test() -> None:
    need_python(); need_venv()
    say("Running tests")
    code = run([str(PY), "-m", "pytest", "-q", "tests"])
    if code == 0:
        say("All tests passed. Next:  python run.py app")
    else:
        fail("Some tests failed (details above).", "read the first failure; it names the file and line.")


def app() -> None:
    need_python(); need_venv()
    say("Starting Listing Doctor at http://localhost:8501  (Ctrl+C to stop)")
    print("   In the app: click 'Use sample: Maria's Newport home', then go through tabs 1 to 4.")
    try:
        run([str(PY), "-m", "streamlit", "run", "app.py", "--browser.gatherUsageStats", "false"])
    except KeyboardInterrupt:
        say("App stopped.")


def key() -> None:
    need_python()
    say("Save your Gemini API key (get one free at https://aistudio.google.com/apikey)")
    value = input("   Paste key and press Enter (leave blank to cancel): ").strip()
    if not value:
        say("No key saved. The app will keep using demo mode.")
        return
    SECRETS.parent.mkdir(exist_ok=True)
    lines = [l for l in (SECRETS.read_text().splitlines() if SECRETS.exists() else [])
             if not l.startswith("GEMINI_API_KEY")]
    lines.append(f'GEMINI_API_KEY = "{value}"')
    SECRETS.write_text("\n".join(lines) + "\n")
    say(f"Saved to {SECRETS.relative_to(ROOT)} (git ignores this file, so it won't be committed).")
    print("   Restart the app to use live Gemini:  python run.py app")


COMMANDS = {"setup": setup, "check": check, "test": test, "app": app, "key": key}

if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    if cmd in ("", "help", "-h", "--help"):
        print(GUIDE)
    elif cmd in COMMANDS:
        COMMANDS[cmd]()
    else:
        print(f"\nUnknown command '{cmd}'.")
        print(GUIDE)
        sys.exit(2)
