"""
floating.py
-----------
The little draggable recording indicator that floats over every other window.

When you minimise the main window while a recording is in progress, this
appears: a small paper-white disc with the bird and a softly pulsing status
dot (red while recording, amber while processing) - calm and compact, in line
with the app's design system. Drag it anywhere; click to bring the app back.

Each frame is composited in PIL (true alpha) and shown on a borderless,
always-on-top window. The corners outside the disc are made transparent with
a hard-edged colour key, so the disc and the bird stay smooth.
"""

import os
import math
import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
    _HAVE_PIL = True
except Exception:
    _HAVE_PIL = False

from yapyapyap import config

_ASSETS = config.ASSETS_DIR
KEY = "#FF00FF"             # transparent colour key (magenta - unused in the art)
PAPER = (255, 254, 251)     # disc fill (theme PAPER)
HAIRLINE = (228, 206, 114)  # theme BORDER_DEEP
YELLOW = (255, 222, 33)     # hover ring (theme YELLOW)
RECORD = (229, 72, 77)      # recording dot (theme RECORD)
PROCESS = (184, 134, 11)    # processing dot (theme AMBER)


def _lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class RecordingIndicator(tk.Toplevel):
    SIZE = 56          # window square
    R = 25             # disc radius
    BIRD = 26          # bird size (px)
    SS = 4             # supersampling for crisp circles

    def __init__(self, root, on_click):
        super().__init__(root)
        self._root = root
        self._on_click = on_click
        self.overrideredirect(True)
        try:
            self.attributes("-topmost", True)
            self.attributes("-transparentcolor", KEY)
        except tk.TclError:
            pass
        self.configure(bg=KEY)

        self.canvas = tk.Canvas(self, width=self.SIZE, height=self.SIZE, bg=KEY,
                                highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()

        self._bird = None
        if _HAVE_PIL:
            try:
                bird = Image.open(
                    os.path.join(_ASSETS, "logo_256.png")).convert("RGBA")
                # The logo art isn't centred within its own canvas, so crop to
                # the bird's actual pixels; we then place THAT centred in the
                # disc (resized per-frame, preserving its aspect ratio).
                bbox = bird.getchannel("A").getbbox()
                if bbox:
                    bird = bird.crop(bbox)
                self._bird = bird
            except Exception:
                self._bird = None
        self._photo = None

        self._phase = 0.0
        self._hover = False
        self._accent = RECORD
        self._anim_on = False
        self._placed = False
        self._drag_dx = self._drag_dy = 0
        self._moved = False

        c = self.canvas
        c.bind("<ButtonPress-1>", self._press)
        c.bind("<B1-Motion>", self._drag)
        c.bind("<ButtonRelease-1>", self._release)
        c.bind("<Enter>", lambda e: setattr(self, "_hover", True))
        c.bind("<Leave>", lambda e: setattr(self, "_hover", False))

        self.withdraw()

    # ---- show / hide -------------------------------------------------
    def show(self, accent=RECORD):
        self._accent = tuple(accent)
        if not self._placed:
            sw = self.winfo_screenwidth()
            self.geometry(f"{self.SIZE}x{self.SIZE}+{sw - self.SIZE - 32}+72")
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

    # ---- animation ---------------------------------------------------
    def _tick(self):
        if not self._anim_on:
            return
        try:
            self._phase = (self._phase + 0.022) % 1.0
            self._render()
            self.after(40, self._tick)
        except tk.TclError:
            self._anim_on = False

    def _render(self):
        if not _HAVE_PIL:
            return self._render_basic()
        ss = self.SS
        S = self.SIZE * ss
        cx = S / 2
        R = self.R * ss
        acc = self._accent

        # Draw on a transparent layer at 4x (smooth interior anti-aliasing),
        # then key it down with a hard-edged mask so the colour key stays clean.
        img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        # Paper disc + hairline (a touch warmer on hover).
        fill = _lerp(PAPER, YELLOW, 0.12) if self._hover else PAPER
        d.ellipse([cx - R, cx - R, cx + R, cx + R], fill=fill + (255,))
        edge = YELLOW if self._hover else HAIRLINE
        d.ellipse([cx - R, cx - R, cx + R, cx + R], outline=edge + (255,),
                  width=2 * ss)

        # The bird, centred (preserving its aspect ratio), nudged up a touch to
        # leave room for the status dot.
        if self._bird is not None:
            bw, bh = self._bird.size
            target = self.BIRD * ss
            scale = target / max(bw, bh)
            nw, nh = max(1, int(bw * scale)), max(1, int(bh * scale))
            bird = self._bird.resize((nw, nh), Image.LANCZOS)
            img.alpha_composite(bird, (int(cx - nw / 2),
                                       int(cx - nh / 2 - 2 * ss)))

        # Status dot (bottom-centre), breathing gently.
        breathe = 0.5 + 0.5 * math.sin(self._phase * 2 * math.pi)
        dy = cx + R - 9.5 * ss
        r_dot = (3.2 + 0.7 * breathe) * ss
        halo = _lerp(acc, fill, 0.45 + 0.35 * (1 - breathe))
        d.ellipse([cx - r_dot - 2 * ss, dy - r_dot - 2 * ss,
                   cx + r_dot + 2 * ss, dy + r_dot + 2 * ss],
                  fill=halo + (255,))
        d.ellipse([cx - r_dot, dy - r_dot, cx + r_dot, dy + r_dot],
                  fill=acc + (255,))

        img = img.resize((self.SIZE, self.SIZE), Image.LANCZOS)
        mask = img.getchannel("A").point(lambda a: 255 if a > 127 else 0)
        out = Image.new("RGBA", img.size, (255, 0, 255, 255))
        out.paste(img, (0, 0), mask)
        self._photo = ImageTk.PhotoImage(out)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)

    def _render_basic(self):
        """Fallback if Pillow is unavailable: plain disc + dot + bird PNG."""
        c = self.canvas
        c.delete("all")
        cx = self.SIZE / 2
        R = self.R
        c.create_oval(cx - R, cx - R, cx + R, cx + R, fill="#FFFEFB",
                      outline="#E4CE72", width=2)
        if not hasattr(self, "_bird_tk"):
            try:
                self._bird_tk = tk.PhotoImage(file=os.path.join(_ASSETS, "logo_32.png"))
            except Exception:
                self._bird_tk = None
        if self._bird_tk:
            c.create_image(cx, cx - 3, image=self._bird_tk)
        breathe = 0.5 + 0.5 * math.sin(self._phase * 2 * math.pi)
        col = "#%02x%02x%02x" % _lerp(self._accent, PAPER, 0.25 * breathe)
        r = 3.5 + breathe
        dy = cx + R - 9
        c.create_oval(cx - r, dy - r, cx + r, dy + r, fill=col, outline=col)

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
