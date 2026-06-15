"""
config.py
---------
All of YapYapYap's settings, persisted in a single JSON file so the app needs no
backend or database - just a folder you can copy around.

Design goals
------------
* **Blank start works.** On first run there's no settings.json; the app simply
  uses the DEFAULTS below and creates its folders on demand.
* **Everything persists.** Any time a setting changes (in the Settings window, or
  the project picker, or the window size) it's written straight back to
  settings.json via save_settings()/update_settings().
* **Safe writes.** Saves are atomic (write a temp file, then replace) so a crash
  or power-cut can never leave a half-written, corrupt settings.json. A corrupt
  file is backed up and the app falls back to defaults rather than failing.
* **Portable.** The default recordings/transcripts folders are stored as blank
  and resolved relative to the app folder at run time, so you can move or rename
  the whole folder and your files still resolve correctly. Only a *custom* folder
  you pick yourself is stored as an absolute path.
* **Read-only safe.** If the folder can't be written to, the app logs a warning
  and keeps running with in-memory settings instead of crashing.

Other modules just read the module-level constants (config.WHISPER_MODEL, etc.),
which are refreshed whenever settings change.
"""

import os
import json
import shutil
import logging

# The folder this app lives in (used to build the default paths below).
BASE = os.path.dirname(os.path.abspath(__file__))

APP_NAME = "YapYapYap"
SETTINGS_FILE = os.path.join(BASE, "settings.json")
SETTINGS_VERSION = 1
LOG_DIR = os.path.join(BASE, "logs")

WHISPER_MODELS = ["tiny", "base", "small", "medium"]

# Built-in default folders. Stored as "" in settings.json (see save_settings) so
# the app stays portable; resolved to these at run time when blank.
DEFAULT_RECORDINGS_DIR = os.path.join(BASE, "recordings")
DEFAULT_TRANSCRIPTS_DIR = os.path.join(BASE, "transcripts")

DEFAULT_SUMMARY_PROMPT = """You are an expert meeting-notes assistant. Below is a \
transcript of a meeting (it may be rough or contain transcription errors). Write \
concise, accurate notes in Markdown.

Strict rules:
- Use ONLY information that is actually present in the transcript. Never invent \
names, numbers, dates, decisions or action items.
- NEVER write placeholders or fill-in-the-blank text such as "[insert ...]", \
"[list ...]", "[main topics]", "TBD", "N/A" or "None specified". If a section \
has no real content, simply leave that section out entirely.
- Do not output a section heading unless you have real content to put under it.
- If the transcript is too short, empty or unclear to summarise, reply with a \
single short sentence saying exactly that, and nothing else.

When there is enough content, use these sections (include a section only when it \
genuinely has content):

## Summary
2-4 sentences on what was discussed and any outcome.

## Key discussion points
- Concise bullets of the main topics.

## Decisions
- Decisions that were actually made.

## Action items / next steps
- [ ] Owner - the task (add a deadline only if one was clearly stated).

## Open questions
- Anything explicitly left unresolved.

TRANSCRIPT:
{transcript}
"""

# --- Defaults (a fresh install behaves exactly like this) ---------------
DEFAULTS = {
    "recordings_dir": "",      # blank => DEFAULT_RECORDINGS_DIR (portable)
    "transcripts_dir": "",     # blank => DEFAULT_TRANSCRIPTS_DIR (portable)
    "whisper_model": "base",   # tiny | base | small | medium
    "summary_model": "llama3.1",
    "summary_prompt": DEFAULT_SUMMARY_PROMPT,
    "projects": [],            # [{"name": str, "path": str}, ...]
    "selected_project": "",    # last project chosen next to Record ("" = none)
    "window_geometry": "",     # remembered main-window geometry
}


def _resolve(value, default):
    return value if value else default


# --------------------------------------------------------------------------
# Load / save
# --------------------------------------------------------------------------
def load_settings():
    """Return settings (DEFAULTS merged with settings.json). Never raises."""
    data = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            data.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass  # fresh install - defaults are fine
    except (OSError, json.JSONDecodeError, ValueError):
        _backup_corrupt()  # don't lose a corrupt file silently
    return data


def save_settings(values):
    """Persist a (possibly partial) settings update, atomically, and publish it.

    `values` is merged over the CURRENT settings, so passing only the keys you
    changed leaves everything else (e.g. the picked project, window size) intact.
    """
    data = load_settings()  # start from what's on disk, not bare defaults
    data.update({k: v for k, v in values.items() if k in DEFAULTS})

    # Keep folders portable: store blank when they're just the built-in default.
    if data["recordings_dir"] in ("", DEFAULT_RECORDINGS_DIR):
        data["recordings_dir"] = ""
    if data["transcripts_dir"] in ("", DEFAULT_TRANSCRIPTS_DIR):
        data["transcripts_dir"] = ""

    payload = dict(data)
    payload["_version"] = SETTINGS_VERSION
    _atomic_write(payload)
    _apply(data)
    return data


def update_settings(**changes):
    """Persist a few changed keys (the rest are preserved). For one-off updates
    like the picked project or the window size."""
    return save_settings(dict(changes))


def _atomic_write(payload):
    """Write settings.json safely (temp file + atomic replace)."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        tmp = SETTINGS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, SETTINGS_FILE)
    except OSError as e:
        logging.getLogger(APP_NAME).warning(
            "Could not write settings.json (%s); continuing with in-memory "
            "settings.", e)


def _backup_corrupt():
    try:
        if os.path.exists(SETTINGS_FILE):
            shutil.copy2(SETTINGS_FILE, SETTINGS_FILE + ".bak")
            logging.getLogger(APP_NAME).warning(
                "settings.json was unreadable; backed it up to settings.json.bak "
                "and reset to defaults.")
    except OSError:
        pass


def _apply(data):
    """Publish a settings dict to the module-level constants other files read."""
    global RECORDINGS_DIR, TRANSCRIPTS_DIR, WHISPER_MODEL, SUMMARY_MODEL
    global SUMMARY_PROMPT, PROJECTS, SELECTED_PROJECT, WINDOW_GEOMETRY
    RECORDINGS_DIR = _resolve(data["recordings_dir"], DEFAULT_RECORDINGS_DIR)
    TRANSCRIPTS_DIR = _resolve(data["transcripts_dir"], DEFAULT_TRANSCRIPTS_DIR)
    WHISPER_MODEL = data["whisper_model"]
    SUMMARY_MODEL = data["summary_model"]
    SUMMARY_PROMPT = data["summary_prompt"]
    PROJECTS = list(data["projects"])
    SELECTED_PROJECT = data["selected_project"]
    WINDOW_GEOMETRY = data["window_geometry"]


def find_project(name):
    """Return the project dict for `name`, or None."""
    for p in PROJECTS:
        if p.get("name") == name:
            return p
    return None


# Populate the constants at import time.
_apply(load_settings())
