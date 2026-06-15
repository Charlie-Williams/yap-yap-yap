"""
process_worker.py
-----------------
The "clean" half of the pipeline. It takes the two raw audio streams captured by
recorder_worker.py, mixes them down to a single 16 kHz mono .wav, and transcribes
that with faster-whisper.

This process never opens an audio capture stream, so it is free of the native
runtime instability that afflicts the recorder process - which is exactly why
all the heavy lifting (scipy resampling + ctranslate2 transcription) lives here.

Live progress
-------------
faster-whisper yields each segment from a generator as it is decoded, and tells
us the total audio duration up front. So this worker streams progress to stdout
as it goes, one event per line, which engine.py reads live to drive the UI:

    @STEP <text>          a new stage started (mixing / loading / transcribing)
    @DUR  <seconds>       total audio length (for a transcription percentage)
    @SEG  <end>\t<line>   one transcribed line, with its end time in seconds
    @OK                   finished successfully

Anything not starting with "@" (e.g. library log noise) is ignored by the parent.

Usage (invoked by engine.py):
    python process_worker.py <mic_wav> <sys_wav> <out_mixed_wav> <model> <out_txt>
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import sys
import wave

import mixer
# NOTE: we deliberately do NOT import `recorder` (and therefore not
# pyaudiowpatch) here, to keep this transcription process entirely free of the
# audio-capture library.


def emit(tag, text=""):
    """Send one progress event to the parent (engine.py)."""
    sys.stdout.write("@%s %s\n" % (tag, text))
    sys.stdout.flush()


def _save_wav(path, frames, channels, rate):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16
        wf.setframerate(rate)
        wf.writeframes(frames)


def _fmt_time(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def main():
    if len(sys.argv) != 6:
        print("usage: process_worker.py <mic> <sys> <out_wav> <model> <out_txt>",
              file=sys.stderr)
        return 2

    mic_wav, sys_wav, out_wav, model_size, out_txt = sys.argv[1:6]

    # 1) Mix the two raw streams into one clean 16 kHz mono signal.
    emit("STEP", "Mixing audio")
    recording = {
        "mic": mixer.load_stream_wav(mic_wav),
        "sys": mixer.load_stream_wav(sys_wav),
    }
    mixed = mixer.mix_streams(recording)
    _save_wav(out_wav, mixer.to_int16(mixed), 1, mixer.TARGET_RATE)

    # 2) Load the model (first run downloads it, which is the slow part).
    emit("STEP", "Loading the Whisper %s model" % model_size.capitalize())
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    # 3) Transcribe, streaming each segment out as it is produced.
    emit("STEP", "Transcribing")
    segments, info = model.transcribe(mixed, beam_size=5)
    emit("DUR", "%.3f" % float(getattr(info, "duration", 0) or 0))

    lines = []
    for seg in segments:
        line = "[%s] %s" % (_fmt_time(seg.start), seg.text.strip())
        lines.append(line)
        emit("SEG", "%.3f\t%s" % (float(seg.end or 0), line))

    transcript = "\n".join(lines).strip()
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(transcript)

    emit("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
