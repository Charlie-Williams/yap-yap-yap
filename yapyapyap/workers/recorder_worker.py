"""
recorder_worker.py
------------------
A standalone recording process. It captures mic + system audio, streaming each
stream straight to its .wav file as it arrives, and on a "stop" signal finalises
both files and exits.

Why this process is deliberately minimal
----------------------------------------
On Windows, once a WASAPI capture stream has been opened in a process, that
process becomes unstable for other heavy native work. We learned this the hard
way: not only does loading Whisper here crash, but even running the scipy
resample used for mixing, or spawning a subprocess, can segfault it (conflicting
native OpenMP runtimes from PortAudio vs numpy/scipy/ctranslate2).

So this process touches NOTHING heavy: only PyAudio (capture) and the standard
library's `wave` module (to save the raw streams). All mixing, resampling and
transcription happen later in a separate, clean process (process_worker.py) that
never opened an audio stream. That is what makes Stop reliable.

Protocol
--------
    python recorder_worker.py <mic_wav> <sys_wav>

Prints "READY" once recording has started. Records until it reads a line
containing "stop" on stdin. Then it saves both raw streams, prints
"OK <duration_seconds>", and hard-exits 0 (skipping the native teardown that
would otherwise segfault). On failure it prints "ERR ..." to stderr and exits 1.
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import sys
import traceback

from yapyapyap.core import recorder  # PyAudio + stdlib wave only - no numpy/scipy/whisper here


def main():
    if len(sys.argv) != 3:
        print("usage: recorder_worker.py <mic_wav> <sys_wav>", file=sys.stderr)
        return 2

    mic_wav, sys_wav = sys.argv[1], sys.argv[2]

    rec = recorder.Recorder(mic_wav, sys_wav)
    try:
        rec.start()
    except Exception as e:
        print("ERR could not start recording: %s" % e, file=sys.stderr)
        traceback.print_exc()
        return 1

    print("READY", flush=True)

    # readline() reacts to "stop" immediately (no read-ahead buffering). An
    # empty string means stdin closed (parent gone), so we stop then too.
    while True:
        line = sys.stdin.readline()
        if not line or "stop" in line.lower():
            break

    try:
        # Hard stop: stop capture without any native PortAudio teardown
        # (no stream.close(), no Pa_Terminate). Those teardown calls are what
        # can segfault a process that opened a WASAPI loopback stream; we
        # hard-exit below instead and let the OS reclaim the device. The .wav
        # files were written continuously and are finalised by stop_hard().
        duration = rec.stop_hard()
        print("OK %.1f" % duration, flush=True)
        return 0
    except Exception as e:
        print("ERR processing failed: %s" % e, file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    code = main()
    # Flush, then hard-exit. This process has opened a WASAPI stream, so its
    # native runtime is in the unstable state that segfaults during a normal
    # interpreter shutdown. Everything is already written and flushed, so we
    # skip Python/native teardown entirely with os._exit.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
