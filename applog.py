"""
applog.py
---------
Sets up logging so you (or I) can debug problems later. Everything the app does
— and any crash it can catch — is written to:

    logs/yapyapyap.log

Call setup() once at startup. If something goes wrong, open that file (or send
it over) and the last lines usually show exactly where it failed.

Note: a truly low-level crash in a native library (e.g. a segfault) can kill the
process without Python getting a chance to log it. But because we log right
BEFORE each risky step ("loading model…", "transcribing…"), the last surviving
log line still tells us which step died.
"""

import logging
import os
import sys
import threading

import config


def setup():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    logfile = os.path.join(config.LOG_DIR, "yapyapyap.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(logfile, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Catch uncaught exceptions on the main thread.
    def _excepthook(exc_type, exc, tb):
        logging.critical("Uncaught exception", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _excepthook

    # Catch uncaught exceptions in background threads (Python 3.8+).
    def _thread_excepthook(args):
        logging.critical(
            "Uncaught exception in thread %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = _thread_excepthook

    log = logging.getLogger(config.APP_NAME)
    log.info("==== %s starting (log: %s) ====", config.APP_NAME, logfile)
    return log
