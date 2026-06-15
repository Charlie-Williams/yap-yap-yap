"""
cli.py - YapYapYap, command-line edition.

A no-window way to use YapYapYap. Press ENTER to start recording, ENTER again to
stop; the transcript and notes are saved to the folders set in Settings (or
config.py / settings.json).

Usage:
    python cli.py                 record a new conversation
    python cli.py --list          list past conversations
    python cli.py --model small   use a different Whisper model this run

Like the GUI, recording and transcription run in isolated worker subprocesses
(see engine.py), so this process never loads the conflicting native audio/ML
runtimes that used to crash it.
"""

import os
import sys
import time
import argparse
import threading

from yapyapyap import config
from yapyapyap import applog
from yapyapyap.core import engine
from yapyapyap.core import summarize

log = applog.setup()


def _fmt_elapsed(seconds):
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"


def _banner():
    print()
    print("  YapYapYap")
    print("  =========")
    print("  Records your mic + the system audio (everyone on the call) and")
    print("  transcribes it locally on your machine.")
    print()


def record_once(model_size):
    os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
    os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

    input("  Press ENTER to START recording... ")

    session = engine.RecordingSession()
    session.start()
    log.info("Recording started.")
    started = time.time()

    stop_timer = threading.Event()

    def tick():
        while not stop_timer.is_set():
            sys.stdout.write(
                f"\r  Recording {_fmt_elapsed(time.time() - started)}  -  press ENTER to stop ")
            sys.stdout.flush()
            time.sleep(0.5)

    timer = threading.Thread(target=tick, daemon=True)
    timer.start()

    input()  # blocks until ENTER
    stop_timer.set()
    timer.join(timeout=1)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    print("  Stopping and transcribing...")
    result = session.stop(model_size=model_size)
    log.info("Captured %.1fs of audio.", result["duration"])

    transcript = result["transcript"]

    # Generate AI notes automatically if Ollama is available.
    notes_path = None
    if transcript and summarize.is_available():
        print("  Writing AI notes...")
        try:
            notes_path, _ = engine.generate_notes(result["base"])
        except summarize.SummarizeError as e:
            print("  (Notes skipped:", e, ")")

    print()
    print("  Done.")
    print("  Audio      :", result["wav"])
    print("  Transcript :", result["transcript_path"])
    if notes_path:
        print("  Notes      :", notes_path)
    print()
    if transcript:
        preview = transcript[:300] + ("..." if len(transcript) > 300 else "")
        print("  Preview:")
        print("  " + preview.replace("\n", "\n  "))
    else:
        print("  (No speech detected.)")
    print()


def list_conversations():
    folder = config.RECORDINGS_DIR
    txts = []
    if os.path.isdir(folder):
        txts = [f for f in os.listdir(folder) if f.endswith("_transcript.txt")]
    if not txts:
        print("  No recordings yet.")
        return
    print("  Past conversations:")
    for f in sorted(txts, reverse=True):
        print("   -", f.replace("_transcript.txt", "").replace("meeting_", ""))


def main():
    parser = argparse.ArgumentParser(description="YapYapYap CLI recorder")
    parser.add_argument("--list", action="store_true",
                        help="list past conversations and exit")
    parser.add_argument("--model", default=config.WHISPER_MODEL,
                        help="Whisper model size: tiny | base | small | medium")
    args = parser.parse_args()

    _banner()

    if args.list:
        list_conversations()
        return

    try:
        while True:
            record_once(args.model)
            again = input("  Record another conversation? [y/N] ").strip().lower()
            print()
            if again != "y":
                break
        print("  Bye.")
        print()
    except KeyboardInterrupt:
        print("\n  Cancelled.")
    except Exception:
        log.exception("CLI error")
        print("\n  Something went wrong - see logs/yapyapyap.log for details.")


if __name__ == "__main__":
    main()
