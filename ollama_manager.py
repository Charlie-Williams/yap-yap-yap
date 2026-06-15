"""
ollama_manager.py
-----------------
Everything needed to manage local AI models from inside the app, so the user
never has to touch a terminal:

  * detect whether Ollama (the local model runner) is installed / running
  * install it (via winget) if it isn't
  * list the models already downloaded
  * download a new model, with live progress
  * a small curated catalogue of good models (name, size, description)

The actual note-writing still happens in summarize.py, which talks to the same
local Ollama server. This module is just the plumbing for "pick a model, hit
download, use it" from the Settings window.
"""

import os
import json
import shutil
import subprocess
import urllib.request
import urllib.error

# Use 127.0.0.1 (not "localhost"): on Windows localhost can resolve to IPv6
# first and stall ~2s before falling back to IPv4, making every call feel slow.
OLLAMA_BASE = "http://127.0.0.1:11434"

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# A curated shortlist of solid, general-purpose models for meeting notes,
# smallest/fastest first. Sizes are approximate download sizes.
CURATED = [
    {"tag": "llama3.2:1b", "label": "Llama 3.2 (1B)", "size": "1.3 GB",
     "desc": "Fastest. Runs well on any laptop; fine for quick notes."},
    {"tag": "gemma2:2b", "label": "Gemma 2 (2B)", "size": "1.6 GB",
     "desc": "Compact and tidy - good structure for its small size."},
    {"tag": "llama3.2:3b", "label": "Llama 3.2 (3B)", "size": "2.0 GB",
     "desc": "Great all-rounder and a sensible default for most machines."},
    {"tag": "mistral:7b", "label": "Mistral (7B)", "size": "4.1 GB",
     "desc": "Strong, well-balanced quality. Needs a little more RAM/time."},
    {"tag": "llama3.1:8b", "label": "Llama 3.1 (8B)", "size": "4.9 GB",
     "desc": "Highest quality here. Best notes if your machine can take it."},
]


# --------------------------------------------------------------- detection
def _find_binary():
    """Locate the ollama executable (winget doesn't always add it to PATH)."""
    found = shutil.which("ollama")
    if found:
        return found
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
        os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def is_installed():
    return _find_binary() is not None


def is_running():
    try:
        with urllib.request.urlopen(OLLAMA_BASE + "/api/tags", timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


def ensure_running():
    """Start the local Ollama server if it's installed but not yet running."""
    if is_running():
        return True
    exe = _find_binary()
    if not exe:
        return False
    try:
        subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=_NO_WINDOW)
    except OSError:
        return False
    # Give the server a moment to come up.
    import time
    for _ in range(20):
        if is_running():
            return True
        time.sleep(0.5)
    return is_running()


def list_installed():
    """Names of models already downloaded (e.g. ['llama3.2:3b'])."""
    try:
        with urllib.request.urlopen(OLLAMA_BASE + "/api/tags", timeout=4) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", [])]
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []


def is_model_installed(tag):
    installed = list_installed()
    # Ollama reports "llama3.2:3b"; a bare "llama3.2" implies ":latest".
    want = tag if ":" in tag else tag + ":latest"
    return want in installed or tag in installed


# --------------------------------------------------------------- install
def install_ollama(on_line=None):
    """
    Install Ollama via winget. Calls on_line(text) with output lines.
    Returns True on success. Blocking - run on a worker thread.
    """
    winget = shutil.which("winget")
    if not winget:
        if on_line:
            on_line("winget isn't available. Please install Ollama from "
                    "https://ollama.com/download")
        return False
    cmd = [winget, "install", "--id", "Ollama.Ollama", "-e",
           "--accept-package-agreements", "--accept-source-agreements"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                creationflags=_NO_WINDOW)
        for line in proc.stdout:
            line = line.strip()
            if line and on_line:
                on_line(line)
        proc.wait()
    except OSError as e:
        if on_line:
            on_line("Install failed: %s" % e)
        return False
    return is_installed()


# --------------------------------------------------------------- download
def pull_model(tag, on_progress=None):
    """
    Download a model via Ollama, streaming progress.
    on_progress(fraction, status) is called as it downloads (fraction 0..1).
    Returns True on success. Raises OllamaError on failure. Blocking.
    """
    if not ensure_running():
        raise OllamaError("Ollama isn't running. Install it first.")

    payload = json.dumps({"name": tag, "stream": True}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_BASE + "/api/pull", data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=None) as resp:
            for raw in resp:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    raise OllamaError(str(obj["error"]))
                status = obj.get("status", "")
                total = obj.get("total") or 0
                completed = obj.get("completed") or 0
                frac = (completed / total) if total else None
                if on_progress:
                    on_progress(frac, status)
    except urllib.error.URLError as e:
        raise OllamaError("Download failed: %s" % e)
    return is_model_installed(tag)


class OllamaError(RuntimeError):
    pass
