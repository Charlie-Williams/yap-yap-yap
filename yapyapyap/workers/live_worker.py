"""
live_worker.py
--------------
Live (during-recording) transcription. While recorder_worker.py streams the two
raw audio streams to disk, this separate, long-lived process loads Whisper ONCE
and transcribes the growing audio in near-real-time, so captions can appear on
screen as people speak. The authoritative, clean transcript is still produced by
process_worker.py when the user presses Stop.

Why a separate process (again)
------------------------------
Same reason as the rest of the pipeline: this process never opens an audio
capture stream, so it is free of the PortAudio/ctranslate2 native conflict and
can safely run Whisper. It only READS the .wav files the recorder is writing.

Keeping up, or bowing out
-------------------------
Live transcription is CPU-heavy. After each window we compare how long
transcription took against how much audio it covered (the real-time factor). If
the machine clearly can't keep up, we print "@FALLBACK" and exit cleanly — the
recording itself is unaffected (it's still streaming to disk) and the full
transcript is produced on Stop as usual.

Protocol
--------
    python -m yapyapyap.workers.live_worker <mic_wav> <sys_wav> <model>

Reads "stop" on stdin to exit. Emits, one event per line:
    @SEG <end_sec>\t<text>   a newly transcribed caption line
    @FALLBACK                gave up live mode (machine can't keep up)
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import sys
import time
import wave
import threading

import numpy as np

from yapyapyap.core import mixer

# Tuning. A window of recent audio is transcribed each pass; a little left-hand
# CONTEXT gives Whisper the lead-in it needs so boundary words aren't clipped.
MIN_WINDOW = 6.0      # don't transcribe until this much new audio has arrived
CONTEXT = 3.0         # seconds of already-committed audio re-fed for context
POLL_SECS = 1.0       # how often to check for new audio
# If transcribing takes longer than the audio it covers (RTF > this) for a few
# windows running, we conclude the machine can't keep up and fall back.
RTF_LIMIT = 1.0
FALLBACK_STRIKES = 3


def _read_slice(path, start_sec, end_sec):
    """Read [start_sec, end_sec) from a (possibly still-growing) stream .wav.
    Returns (float32_mono_16k, available_sec). Tolerant of transient read
    errors while the recorder is mid-checkpoint."""
    try:
        with wave.open(path, "rb") as wf:
            rate = wf.getframerate()
            ch = wf.getnchannels()
            n = wf.getnframes()
            available = n / rate if rate else 0.0
            s = max(0, int(start_sec * rate))
            e = min(n, int(end_sec * rate))
            if e <= s:
                return None, available
            wf.setpos(s)
            frames = wf.readframes(e - s)
        return mixer.pcm_to_16k_mono(frames, rate, ch), available
    except (OSError, EOFError, wave.Error):
        return None, 0.0


def emit(tag, text=""):
    sys.stdout.write("@%s %s\n" % (tag, text))
    sys.stdout.flush()


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def main():
    if len(sys.argv) != 4:
        print("usage: live_worker.py <mic_wav> <sys_wav> <model>", file=sys.stderr)
        return 2
    mic_wav, sys_wav, model_size = sys.argv[1], sys.argv[2], sys.argv[3]

    # Stop when the parent says so (or closes our stdin).
    stop = threading.Event()

    def watch_stdin():
        while True:
            line = sys.stdin.readline()
            if not line or "stop" in line.lower():
                stop.set()
                return

    threading.Thread(target=watch_stdin, daemon=True).start()

    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    committed = 0.0      # seconds of audio already turned into committed captions
    strikes = 0

    while not stop.is_set():
        # How much aligned audio is available from BOTH streams right now?
        _, mic_avail = _read_slice(mic_wav, 0, 0)
        _, sys_avail = _read_slice(sys_wav, 0, 0)
        available = min(mic_avail, sys_avail)

        if available - committed < MIN_WINDOW:
            time.sleep(POLL_SECS)
            continue

        win_start = max(0.0, committed - CONTEXT)
        win_end = available
        mic_audio, _ = _read_slice(mic_wav, win_start, win_end)
        sys_audio, _ = _read_slice(sys_wav, win_start, win_end)
        if mic_audio is None and sys_audio is None:
            time.sleep(POLL_SECS)
            continue
        mixed = mixer.mix_two(
            mic_audio if mic_audio is not None else np.zeros(0, dtype=np.float32),
            sys_audio if sys_audio is not None else np.zeros(0, dtype=np.float32))

        window_audio_secs = win_end - win_start
        t0 = time.time()
        segments, _info = model.transcribe(mixed, beam_size=1)
        new_committed = committed
        for seg in segments:
            abs_start = win_start + (seg.start or 0.0)
            abs_end = win_start + (seg.end or 0.0)
            # Only commit segments that begin at/after what we've already shown
            # (the CONTEXT region is just lead-in and was committed last pass).
            if abs_start < committed - 0.25:
                continue
            text = (seg.text or "").strip()
            if not text:
                continue
            emit("SEG", "%.3f\t[%s] %s" % (abs_end, _fmt_time(abs_start), text))
            new_committed = max(new_committed, abs_end)
        # If nothing new committed, still advance so we don't re-chew the window.
        committed = max(new_committed, win_end - CONTEXT)

        elapsed = time.time() - t0
        rtf = (elapsed / window_audio_secs) if window_audio_secs > 0 else 0.0
        if rtf > RTF_LIMIT:
            strikes += 1
            if strikes >= FALLBACK_STRIKES:
                emit("FALLBACK")
                return 0
        else:
            strikes = 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
