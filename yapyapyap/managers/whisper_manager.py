"""
whisper_manager.py
------------------
Manage the local speech-to-text (Whisper) models, mirroring ollama_manager for
the note-writing models. faster-whisper downloads its models from Hugging Face
and caches them; this module lets the Settings window list which are downloaded,
download new ones with progress, and pick which one transcribes.

Downloading happens in a subprocess (whisper_dl_worker.py) so it never blocks the
UI and never loads PortAudio into the app process.
"""

import os
import sys
import time
import threading
import subprocess

from yapyapyap import config

# Downloaded in a subprocess launched as a module so it imports cleanly as part
# of the package (see whisper_dl_worker.py).
_DL_WORKER = "yapyapyap.workers.whisper_dl_worker"
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _worker_env():
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (config.SRC_ROOT + os.pathsep + existing
                         if existing else config.SRC_ROOT)
    return env

# Curated transcription models, smallest/fastest first. size_mb is the approx
# download size (used only to drive the progress bar).
CATALOG = [
    {"size": "tiny", "label": "Whisper Tiny", "human": "75 MB", "size_mb": 75,
     "desc": "Fastest. Fine for clear audio and quick drafts."},
    {"size": "base", "label": "Whisper Base", "human": "145 MB", "size_mb": 145,
     "desc": "A good balance of speed and accuracy - sensible default."},
    {"size": "small", "label": "Whisper Small", "human": "480 MB", "size_mb": 480,
     "desc": "More accurate, especially with accents or crosstalk."},
    {"size": "medium", "label": "Whisper Medium", "human": "1.5 GB", "size_mb": 1530,
     "desc": "Best accuracy here. Slower; needs more RAM."},
]


def _repo(size):
    return "Systran/faster-whisper-" + size


def _cache_dir(size):
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
        base = HF_HUB_CACHE
    except Exception:
        base = os.path.expanduser("~/.cache/huggingface/hub")
    return os.path.join(base, "models--Systran--faster-whisper-" + size)


def is_downloaded(size):
    try:
        from huggingface_hub import try_to_load_from_cache
        path = try_to_load_from_cache(_repo(size), "model.bin")
        return isinstance(path, str) and os.path.exists(path)
    except Exception:
        # Fallback: a populated cache dir with a model.bin somewhere in it.
        d = _cache_dir(size)
        if not os.path.isdir(d):
            return False
        for root, _dirs, files in os.walk(d):
            if "model.bin" in files:
                return True
        return False


def downloaded_sizes():
    return [m["size"] for m in CATALOG if is_downloaded(m["size"])]


def _dir_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for fn in files:
            try:
                total += os.path.getsize(os.path.join(root, fn))
            except OSError:
                pass
    return total


def download(size, on_progress=None):
    """
    Download a Whisper model in a subprocess, reporting progress by polling the
    cache directory against the model's approximate size. Returns True on
    success. Blocking - run on a worker thread.
    """
    expected = next((m["size_mb"] for m in CATALOG if m["size"] == size), 0) * 1024 * 1024
    proc = subprocess.Popen([sys.executable, "-m", _DL_WORKER, size],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, creationflags=_NO_WINDOW, env=_worker_env())

    stop = threading.Event()

    def poll():
        d = _cache_dir(size)
        while not stop.is_set():
            got = _dir_bytes(d) if os.path.isdir(d) else 0
            frac = min(got / expected, 0.99) if expected else None
            if on_progress:
                on_progress(frac, "downloading")
            time.sleep(0.5)

    t = threading.Thread(target=poll, daemon=True)
    t.start()
    proc.wait()
    stop.set()
    if on_progress:
        on_progress(1.0, "done")
    return is_downloaded(size)
