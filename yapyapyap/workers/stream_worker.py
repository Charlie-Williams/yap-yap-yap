"""
stream_worker.py
----------------
Background "head-start" transcription. This runs DURING recording in a separate,
clean process (it never opens an audio capture stream, so it can safely load
Whisper) and transcribes the meeting as it is recorded — using the SAME accurate
model the final transcript uses. By the time you press Stop, most of the audio
has already been transcribed, so finishing only needs the short remaining tail.
That makes Stop fast even with a slow, accurate model.

It reads the growing .mic.wav / .sys.wav stems the recorder is writing, mixes
short windows to 16 kHz mono and transcribes them, keeping a running list of
committed transcript lines. On a "finalize" command (sent when the user presses
Stop, once the stems are complete) it transcribes whatever tail remains, writes
the full mixed .wav archive and the final transcript, emits "@OK" and exits.

If anything goes wrong (can't read the growing files, model trouble, etc.) it
simply never reports "@OK" and the app falls back to a normal full pass — so the
recording is never at risk.

Protocol
--------
    python -m yapyapyap.workers.stream_worker <mic> <sys> <model> <out_wav> <out_txt>

stdin commands (one per line):
    finalize   transcribe the tail, write outputs, emit @OK, exit
    cancel     exit immediately without writing anything

stdout events (only emitted during finalize; silent while recording):
    @DUR  <total_sec>        total audio length
    @BAR  <fraction>         jump the progress bar to the already-done portion
    @SEG  <end_sec>\t<line>  one transcript line (the streamed tail)
    @OK                      finished; transcript + wav written
"""
import os

# This runs DURING the meeting, so it takes only a conservative share of the
# cores (see config) — leaving the recording, the meeting app and the system
# responsive even on modest machines. Must be set before numpy import.
from yapyapyap import config
_CPU_THREADS = config.background_cpu_threads()
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", str(_CPU_THREADS))

import sys
import time
import wave
import threading

import numpy as np

from yapyapyap.core import mixer

# No captions are shown, so window latency doesn't matter — use large windows
# for efficiency and accuracy (fewer transcribe calls, more context each).
MIN_WINDOW = 20.0     # transcribe once this much new audio has accumulated
MAX_WINDOW = 120.0    # never transcribe more than this at once (bounds memory /
                      # keeps progress smooth if the machine falls behind)
CONTEXT = 2.0         # seconds of prior audio re-fed so boundary words aren't cut
POLL_SECS = 1.0
# Greedy decoding (beam_size=1) is ~2x faster than beam search on CPU with
# near-identical text — measured on this app's medium model. Speed matters far
# more here than the marginal accuracy of a wider beam.
BEAM = 1


def _read_slice(path, start_sec, end_sec):
    """Read [start_sec, end_sec) from a (possibly still-growing) stream .wav.
    Returns (float32_mono_16k_or_None, available_sec)."""
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


def _available(mic_wav, sys_wav):
    """How much audio BOTH streams have (the conservative figure used while
    recording, since both are still growing)."""
    _, mic = _read_slice(mic_wav, 0, 0)
    _, syd = _read_slice(sys_wav, 0, 0)
    return min(mic, syd)


def _available_full(mic_wav, sys_wav):
    """The full length to transcribe at finalize — the longer of the two
    finalized streams, so the tail of a slightly-longer stream isn't dropped
    (mixing pads the shorter one, matching the normal full pass)."""
    _, mic = _read_slice(mic_wav, 0, 0)
    _, syd = _read_slice(sys_wav, 0, 0)
    return max(mic, syd)


def emit(tag, text=""):
    sys.stdout.write("@%s %s\n" % (tag, text))
    sys.stdout.flush()


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def _transcribe_window(model, mic_wav, sys_wav, win_start, win_end, committed,
                       segs, stream=False):
    """Transcribe [win_start, win_end], appending newly-committed lines (those
    starting at/after `committed`) to `segs`. If `stream`, also emit each new
    line as a @SEG event as it is decoded (used at finalize so the progress bar
    and transcript-so-far move smoothly). Returns the latest committed end time."""
    mic_audio, _ = _read_slice(mic_wav, win_start, win_end)
    sys_audio, _ = _read_slice(sys_wav, win_start, win_end)
    if mic_audio is None and sys_audio is None:
        return committed
    mixed = mixer.mix_two(
        mic_audio if mic_audio is not None else np.zeros(0, dtype=np.float32),
        sys_audio if sys_audio is not None else np.zeros(0, dtype=np.float32))
    if len(mixed) == 0:
        return committed
    segments, _info = model.transcribe(mixed, beam_size=BEAM)
    last = committed
    for seg in segments:
        abs_start = win_start + (seg.start or 0.0)
        abs_end = win_start + (seg.end or 0.0)
        if abs_start < committed - 0.25:
            continue  # already covered by an earlier window
        text = (seg.text or "").strip()
        if not text:
            continue
        line = "[%s] %s" % (_fmt_time(abs_start), text)
        segs.append((abs_end, line))
        if stream:
            emit("SEG", "%.3f\t%s" % (abs_end, line))
        last = max(last, abs_end)
    return last


def _save_wav(path, frames, channels, rate):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(frames)


def main():
    if len(sys.argv) != 6:
        print("usage: stream_worker.py <mic> <sys> <model> <out_wav> <out_txt>",
              file=sys.stderr)
        return 2
    mic_wav, sys_wav, model_size, out_wav, out_txt = sys.argv[1:6]

    cmd = {"finalize": False, "cancel": False}

    def watch_stdin():
        while True:
            line = sys.stdin.readline()
            if not line:
                cmd["finalize"] = True  # parent gone: finish up with what we have
                return
            low = line.lower()
            if "cancel" in low:
                cmd["cancel"] = True
                return
            if "finalize" in low:
                cmd["finalize"] = True
                return

    threading.Thread(target=watch_stdin, daemon=True).start()

    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8",
                         cpu_threads=_CPU_THREADS)

    committed = 0.0
    segs = []

    # Phase 1: keep up with the recording while it's in progress. Windows are
    # capped at MAX_WINDOW so a machine that falls behind still processes in
    # bounded chunks rather than one ever-growing slice.
    while not cmd["finalize"] and not cmd["cancel"]:
        available = _available(mic_wav, sys_wav)
        if available - committed >= MIN_WINDOW:
            win_start = max(0.0, committed - CONTEXT)
            win_end = min(available, committed + MAX_WINDOW)
            last = _transcribe_window(model, mic_wav, sys_wav, win_start,
                                      win_end, committed, segs)
            committed = max(last, win_end - CONTEXT)
        else:
            time.sleep(POLL_SECS)

    if cmd["cancel"]:
        return 0

    # Phase 2: finalize. The stems are complete now. Tell the UI the total
    # length, jump the bar to the portion already transcribed during recording,
    # then drain the remaining tail in bounded chunks, streaming each line live.
    available = _available_full(mic_wav, sys_wav)
    emit("DUR", "%.3f" % available)
    if available > 0:
        emit("BAR", "%.4f" % max(0.0, min(committed / available, 1.0)))
    while available - committed > 0.05:
        win_start = max(0.0, committed - CONTEXT)
        win_end = min(available, committed + MAX_WINDOW)
        last = _transcribe_window(model, mic_wav, sys_wav, win_start, win_end,
                                  committed, segs, stream=True)
        new_committed = max(last, win_end)  # advance fully so the loop drains
        if new_committed <= committed:
            break  # safety: no progress, avoid an infinite loop
        committed = new_committed

    segs.sort(key=lambda x: x[0])
    transcript = "\n".join(line for _e, line in segs).strip()
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(transcript)

    # Write the full mixed .wav archive (same format process_worker produces).
    try:
        recording = {"mic": mixer.load_stream_wav(mic_wav),
                     "sys": mixer.load_stream_wav(sys_wav)}
        mixed_full = mixer.mix_streams(recording)
        _save_wav(out_wav, mixer.to_int16(mixed_full), 1, mixer.TARGET_RATE)
    except Exception:
        pass  # transcript is the important part; archive wav is best-effort

    emit("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
