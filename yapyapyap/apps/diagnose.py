"""
diagnose.py
-----------
Reproduces the app's EXACT transcription conditions in stages, to find which
one crashes. Run it in the same Python you run the app with:

    python diagnose.py

Watch which "TEST" line prints last. If the program vanishes right after a
"running..." line, THAT stage is the native crash. Copy all output and send it.
"""

import sys
import os
import glob
import wave
import threading
import traceback

import numpy as np

from yapyapyap import config

MODEL = config.WHISPER_MODEL  # what the app actually uses (e.g. "base")

print("=" * 60)
print("PYTHON :", sys.version.split()[0], "|", sys.executable)
print("MODEL  :", MODEL)
print("=" * 60)
sys.stdout.flush()

from faster_whisper import WhisperModel


def transcribe_array(model_size, audio, beam):
    m = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = m.transcribe(audio, beam_size=beam)
    return list(segments)  # force the generator to actually run


def stage(name, fn):
    print(f"\n--- TEST: {name} ... running (watch for a crash here) ---")
    sys.stdout.flush()
    try:
        fn()
        print(f"PASS: {name}")
    except Exception:
        print(f"PYTHON ERROR in '{name}':")
        traceback.print_exc()
    sys.stdout.flush()


silent = np.zeros(16000 * 2, dtype=np.float32)

# 1) app's model, main thread, silent audio, beam_size=5 (app uses 5)
stage(f"{MODEL} | main thread | silent | beam=5",
      lambda: transcribe_array(MODEL, silent, 5))

# 2) app's model, BACKGROUND thread (this is how the app runs it)
def in_thread():
    box = {}
    def work():
        try:
            transcribe_array(MODEL, silent, 5)
        except Exception:
            box["err"] = traceback.format_exc()
    t = threading.Thread(target=work)
    t.start()
    t.join()
    if "err" in box:
        raise RuntimeError(box["err"])

stage(f"{MODEL} | BACKGROUND thread | silent | beam=5", in_thread)

# 3) app's model on your REAL recorded audio (the actual saved .wav)
wavs = sorted(glob.glob(os.path.join(config.RECORDINGS_DIR, "meeting_*.wav")))
if wavs:
    newest = wavs[-1]
    print(f"\n(Found a real recording to test: {os.path.basename(newest)})")

    def real_audio():
        with wave.open(newest, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        transcribe_array(MODEL, audio, 5)

    stage(f"{MODEL} | main thread | REAL audio | beam=5", real_audio)
else:
    print("\n(No saved meeting_*.wav found, skipping the real-audio test.)")

print("\n=== If you saw PASS on every test above, transcription is fine and the")
print("=== crash is elsewhere. If the program vanished, the last 'running' line")
print("=== names the culprit. Send me everything above.")
