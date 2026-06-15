"""
whisper_dl_worker.py
--------------------
Downloads a faster-whisper model into the local cache, then exits. Run as a
subprocess by whisper_manager.download() so the download is isolated from the UI
process (and never loads PortAudio).

    python whisper_dl_worker.py <size>
"""
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "4")

import sys


def main():
    if len(sys.argv) != 2:
        print("usage: whisper_dl_worker.py <size>", file=sys.stderr)
        return 2
    size = sys.argv[1]
    # Constructing the model downloads + caches its files.
    from faster_whisper import WhisperModel
    WhisperModel(size, device="cpu", compute_type="int8")
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
