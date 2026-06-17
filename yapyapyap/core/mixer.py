"""
mixer.py
--------
Takes the two raw audio streams captured by recorder.py (mic + system audio,
each possibly at a different sample rate and channel count) and turns them into
a single clean 16 kHz mono signal — exactly the format Whisper wants.

Doing this AFTER recording (rather than live) is what keeps the tool simple and
robust: we just line the two streams up by length and add them together.
"""

import wave
from math import gcd

import numpy as np
from scipy.signal import resample_poly

TARGET_RATE = 16000  # Whisper's native sample rate


def load_stream_wav(path):
    """Read a raw stream .wav saved by recorder_worker into a stream dict
    (frames bytes + rate + channels) - the shape mix_streams expects.

    Tolerant by design: if one stream is missing, empty or unreadable (e.g. a
    mic that captured nothing), we return a silent stream so the other side
    still gets transcribed instead of the whole run failing."""
    try:
        with wave.open(path, "rb") as wf:
            return {
                "frames": wf.readframes(wf.getnframes()),
                "rate": wf.getframerate(),
                "channels": wf.getnchannels(),
            }
    except (OSError, EOFError, wave.Error):
        return {"frames": b"", "rate": TARGET_RATE, "channels": 1}


def _bytes_to_mono_float(frames, channels):
    """Convert raw int16 bytes -> float32 mono array in range [-1, 1]."""
    if len(frames) == 0:
        return np.zeros(0, dtype=np.float32)
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        # Reshape to (samples, channels) and average down to mono.
        usable = (len(audio) // channels) * channels
        audio = audio[:usable].reshape(-1, channels).mean(axis=1)
    return audio


def _resample(audio, orig_rate):
    """Resample a mono float array to TARGET_RATE."""
    if len(audio) == 0 or orig_rate == TARGET_RATE:
        return audio
    g = gcd(orig_rate, TARGET_RATE)
    up = TARGET_RATE // g
    down = orig_rate // g
    return resample_poly(audio, up, down).astype(np.float32)


def pcm_to_16k_mono(frames, rate, channels):
    """Convert a raw int16 PCM byte slice to a float32 mono array at 16 kHz.
    Used by the live transcriber to process short windows of the growing
    streams without going through the full mix_streams() path."""
    return _resample(_bytes_to_mono_float(frames, channels), rate)


def mix_two(mic_audio, sys_audio):
    """Sum two already-16 kHz-mono float arrays (length-aligned), guarding
    against clipping. Returns a float32 mono array."""
    n = max(len(mic_audio), len(sys_audio))
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    mic_audio = np.pad(mic_audio, (0, n - len(mic_audio)))
    sys_audio = np.pad(sys_audio, (0, n - len(sys_audio)))
    mixed = mic_audio + sys_audio
    peak = np.max(np.abs(mixed)) if len(mixed) else 0.0
    if peak > 1.0:
        mixed = mixed / peak
    return mixed.astype(np.float32)


def mix_streams(recording):
    """
    recording: the dict returned by Recorder.stop().
    Returns a single float32 mono numpy array at 16 kHz, ready for Whisper.
    """
    mic = recording["mic"]
    sys = recording["sys"]

    mic_audio = _resample(_bytes_to_mono_float(mic["frames"], mic["channels"]), mic["rate"])
    sys_audio = _resample(_bytes_to_mono_float(sys["frames"], sys["channels"]), sys["rate"])

    # Pad the shorter stream with silence so both are the same length.
    n = max(len(mic_audio), len(sys_audio))
    if n == 0:
        return np.zeros(0, dtype=np.float32)
    mic_audio = np.pad(mic_audio, (0, n - len(mic_audio)))
    sys_audio = np.pad(sys_audio, (0, n - len(sys_audio)))

    # Sum the two voices. Then guard against clipping by scaling down only if
    # the combined peak exceeds 1.0 (preserves volume in the common case).
    mixed = mic_audio + sys_audio
    peak = np.max(np.abs(mixed)) if len(mixed) else 0.0
    if peak > 1.0:
        mixed = mixed / peak

    return mixed.astype(np.float32)


def to_int16(mixed):
    """Convert the float mix back to int16 bytes for saving a .wav archive."""
    clipped = np.clip(mixed, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()
