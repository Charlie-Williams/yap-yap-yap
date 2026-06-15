"""
app.py
------
The system-tray version of YapYapYap. Lives near the Windows clock as a small
icon you click to start/stop recording a meeting.

The main app is gui.py (a proper window). This tray version is optional - same
engine, no window.

Run it with:   python app.py

Like the GUI it drives isolated worker subprocesses (engine.py), so it never
loads the conflicting native audio/ML runtimes in-process.
"""

import os
import threading

import pystray
from PIL import Image, ImageDraw

import config
import applog
import engine
import summarize

log = applog.setup()


class YapYapYapTray:
    def __init__(self):
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
        self.session = None
        self.state = "idle"  # idle | recording | processing
        self.icon = pystray.Icon("yapyapyap", self._make_icon(), config.APP_NAME)
        self.icon.menu = pystray.Menu(
            pystray.MenuItem(self._toggle_label, self._on_toggle),
            pystray.MenuItem("Open recordings folder", self._open_folder),
            pystray.MenuItem("Quit", self._on_quit),
        )

    # ---- icon drawing -------------------------------------------------
    def _make_icon(self):
        """The cheerful bird, with a small status dot when busy."""
        logo = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "assets", "logo_64.png")
        try:
            img = Image.open(logo).convert("RGBA").resize((64, 64))
        except Exception:
            img = Image.new("RGBA", (64, 64), (255, 222, 33, 255))
        dot = {"recording": (229, 72, 77), "processing": (184, 134, 11)}.get(self.state)
        if dot:
            d = ImageDraw.Draw(img)
            d.ellipse([42, 42, 62, 62], fill=dot, outline=(255, 255, 255), width=2)
        return img

    def _refresh_icon(self):
        self.icon.icon = self._make_icon()
        self.icon.update_menu()

    def _toggle_label(self, item):
        return {"idle": "Start recording",
                "recording": "Stop recording",
                "processing": "Processing..."}[self.state]

    # ---- menu actions -------------------------------------------------
    def _on_toggle(self, icon, item):
        if self.state == "idle":
            self._start()
        elif self.state == "recording":
            self._stop()
        # ignore clicks while processing

    def _open_folder(self, icon, item):
        os.startfile(config.RECORDINGS_DIR)  # Windows-only; opens Explorer

    def _on_quit(self, icon, item):
        if self.state == "recording" and self.session:
            self.session.cancel()
        icon.stop()

    # ---- recording lifecycle -----------------------------------------
    def _start(self):
        try:
            log.info("Starting recording...")
            self.session = engine.RecordingSession()
            self.session.start()
            self.state = "recording"
            self._refresh_icon()
            self.icon.notify("Recording started", config.APP_NAME)
            log.info("Recording started.")
        except Exception as e:
            log.exception("Failed to start recording")
            self.icon.notify(f"Could not start: {e}", config.APP_NAME)
            self.session = None
            self.state = "idle"
            self._refresh_icon()

    def _stop(self):
        log.info("Stop pressed - beginning processing.")
        self.state = "processing"
        self._refresh_icon()
        self.icon.notify("Recording stopped - transcribing...", config.APP_NAME)
        threading.Thread(target=self._process, daemon=True).start()

    def _process(self):
        try:
            result = self.session.stop(model_size=config.WHISPER_MODEL)
            log.info("Captured %.1fs of audio.", result["duration"])
            msg = "Transcript saved."
            if result["transcript"] and summarize.is_available():
                try:
                    engine.generate_notes(result["base"])
                    msg = "Notes + transcript saved."
                except summarize.SummarizeError:
                    pass
            self.icon.notify(msg, config.APP_NAME)
        except Exception as e:
            log.exception("Processing failed")
            self.icon.notify(f"Error: {e}", config.APP_NAME)
        finally:
            self.session = None
            self.state = "idle"
            self._refresh_icon()

    def run(self):
        self.icon.run()


if __name__ == "__main__":
    YapYapYapTray().run()
