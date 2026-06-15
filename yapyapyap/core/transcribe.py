"""
transcribe.py
-------------
In-process speech-to-text via faster-whisper - a fast, CPU-friendly Whisper
reimplementation. No internet, no API key; audio never leaves your machine.

NOTE: the app does NOT call this directly. Because PortAudio and ctranslate2
clash natively on Windows, the app runs transcription in a separate process
(process_worker.py, orchestrated by engine.py). This module is the plain,
in-process implementation, kept for tools that never record audio in the same
process - e.g. diagnose.py and quick experiments.

The model downloads automatically on first use (a few hundred MB) and caches.
"""

_model = None


def _get_model(model_size="base", device="cpu", compute_type="int8"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model


def transcribe(audio, model_size="base"):
    """
    audio: float32 mono numpy array at 16 kHz (from mixer.mix_streams).
    Returns a single transcript string with rough timestamps per segment.
    """
    model = _get_model(model_size=model_size)
    segments, _info = model.transcribe(audio, beam_size=5)

    lines = []
    for seg in segments:
        lines.append(f"[{_fmt_time(seg.start)}] {seg.text.strip()}")
    return "\n".join(lines).strip()


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"
