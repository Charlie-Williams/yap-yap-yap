"""
floating.py
-----------
The little draggable recording indicator that floats over every other window.

When you minimise the main window while a recording is in progress, this
appears: a squared, ink-bordered yellow slab with a red REC dot, an all-caps
REC eyebrow and a big Bricolage timer, in line with the app's editorial
brutalist look. The recording moment is the hero, so even minimised it stays
loud and legible. Drag it anywhere; click to bring the app back.

It is a plain borderless, always-on-top Tk window (no transparency or image
compositing needed for a hard rectangular slab), so it stays crisp on every
platform. The status dot breathes while recording and respects reduced motion.
"""

import sys
import tkinter as tk

from yapyapyap.ui import theme as T

# Defaults kept as RGB tuples for back-compat with callers that pass an accent
# colour (e.g. App._update_indicator passes the record red).
RECORD = (229, 72, 77)      # recording dot (theme RECORD)
PROCESS = (184, 134, 11)    # processing dot (theme AMBER)


def _hex(c):
    """Accept an (r,g,b) tuple or a #rrggbb string; return #rrggbb."""
    if isinstance(c, str):
        return c
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


class RecordingIndicator(tk.Toplevel):
    W = 150            # window width
    H = 60             # window height
    LIP = 3            # ink bottom lip (slab depth)

    def __init__(self, root, on_click):
        super().__init__(root)
        self._root = root
        self._on_click = on_click
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.configure(bg=T.INK)

        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg=T.INK,
                                highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()

        self._accent = _hex(RECORD)
        self._time = "00:00"
        self._pulse_on = True
        self._hover = False
        self._anim_on = False
        self._placed = False
        self._drag_dx = self._drag_dy = 0
        self._moved = False

        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Enter>", lambda e: self._set_hover(True))
        c.bind("<Leave>", lambda e: self._set_hover(False))

        self.withdraw()

    def _set_hover(self, on):
        self._hover = on
        if self._anim_on:
            self._draw()

    # ---- show / hide -------------------------------------------------
    def show(self, accent=RECORD):
        self._accent = _hex(accent)
        if not self._placed:
            sw = self.winfo_screenwidth()
            self.geometry(f"{self.W}x{self.H}+{sw - self.W - 32}+72")
            self._placed = True
        self.deiconify()
        self.lift()
        try:
            self.attributes("-topmost", True)
        except tk.TclError:
            pass
        if not self._anim_on:
            self._anim_on = True
            self._tick()

    def hide(self):
        self._anim_on = False
        self.withdraw()

    def set_time(self, t):
        """Update the displayed timer (called from the main window's tick)."""
        self._time = t
        if self._anim_on:
            try:
                self._draw()
            except tk.TclError:
                pass

    # ---- animation ---------------------------------------------------
    def _tick(self):
        if not self._anim_on:
            return
        try:
            # Reduced motion: hold the dot solid (no breathing); still draw once.
            self._pulse_on = True if T.MOTION.reduced else (not self._pulse_on)
            self._draw()
            if not T.MOTION.reduced:
                self.after(T.MOTION.PULSE // 2, self._tick)
        except tk.TclError:
            self._anim_on = False

    def _draw(self):
        c = self.canvas
        c.delete("all")
        W, H, lip = self.W, self.H, self.LIP
        # Ink base doubles as the 2px border and the deep bottom lip.
        c.create_rectangle(0, 0, W, H, fill=T.INK, outline=T.INK)
        # Yellow slab face, lifted off the ink lip.
        face = T.RAIL_HOVER if self._hover else T.YELLOW
        fy2 = H - lip
        c.create_rectangle(2, 2, W - 2, fy2 - 1, fill=face, outline=face)
        cy = (2 + fy2) / 2

        # Breathing red record dot.
        dot = self._accent if self._pulse_on else T.mix(self._accent, face, 0.55)
        r = 5
        dx = 18
        c.create_oval(dx - r, cy - r, dx + r, cy + r, fill=dot, outline=dot)

        # REC eyebrow (all-caps, tracked) + big Bricolage timer, stacked.
        tx = 32
        c.create_text(tx, cy - 11, text="R E C", anchor="w", fill=T.INK,
                      font=T.bold(8))
        c.create_text(tx, cy + 7, text=self._time, anchor="w", fill=T.INK,
                      font=T.brand(19))

    # ---- drag / click ------------------------------------------------
    def _press(self, e):
        self._drag_dx, self._drag_dy = e.x, e.y
        self._moved = False

    def _drag(self, e):
        self._moved = True
        self.geometry(f"+{self.winfo_pointerx() - self._drag_dx}"
                      f"+{self.winfo_pointery() - self._drag_dy}")

    def _release(self, e):
        if not self._moved and self._on_click:
            self._on_click()
