"""
theme.py
--------
The look and feel of YapYapYap: the bold yellow "workspace rail" design system.

Palette: yellow (#FFDE21) is the identity - the rail, highlights and primary
accents - over a warm cream list column and a near-white "paper" reading
surface, with near-black ink text. High contrast, friendly, premium.

Type: Bricolage Grotesque (display - wordmark, headings, the big timer) and
Hanken Grotesk (everything else). Static instances are bundled in assets/fonts
with one GDI family per weight, loaded privately at import; if loading fails Tk
falls back gracefully to Segoe UI.

Widgets: rounded buttons (with an optional darker bottom "lip"), segmented
tabs, icon buttons, a line-icon set drawn on canvas, white popover menus, a
search field and a scroll container.
"""

import os
import sys
import glob
import math
import tkinter as tk
import tkinter.font as tkfont

from yapyapyap import config


# --- Bundled fonts ------------------------------------------------------
def _load_bundled_fonts():
    d = os.path.join(config.ASSETS_DIR, "fonts")
    if os.name == "nt":
        # Windows: register each TTF privately for this process via GDI.
        import ctypes
        try:
            for ttf in glob.glob(os.path.join(d, "*.ttf")):
                ctypes.windll.gdi32.AddFontResourceExW(
                    ctypes.c_wchar_p(ttf), 0x10, 0)
        except Exception:
            pass
    elif sys.platform == "darwin":
        # macOS Tk has no private-font API, so make the bundled faces available
        # by copying them into the user's font library (idempotent). Tk picks
        # them up on launch; if anything fails we fall back to the system font.
        import shutil
        dest = os.path.expanduser("~/Library/Fonts")
        try:
            os.makedirs(dest, exist_ok=True)
            for ttf in glob.glob(os.path.join(d, "*.ttf")):
                target = os.path.join(dest, os.path.basename(ttf))
                if not os.path.exists(target):
                    shutil.copy2(ttf, target)
        except Exception:
            pass


_load_bundled_fonts()

# Family names (as named inside the bundled TTFs - one family per weight).
BRAND_FAMILY = "Bricolage Grotesque ExtraBold"   # wordmark (800)
HEAD_FAMILY = "Bricolage Grotesque"              # headings / big timer (700)
UI_FAMILY = "Hanken Grotesk"                     # body (400)
UI_MED = "Hanken Grotesk Medium"                 # 500
UI_SEMI = "Hanken Grotesk SemiBold"              # 600
UI_BOLD = "Hanken Grotesk Bold"                  # 700


# --- Palette ------------------------------------------------------------
YELLOW = "#FFDE21"        # brand: rail fill, primary highlights
YELLOW_HOVER = "#FFD400"  # hover on yellow primary
YELLOW_DEEP = "#E7C400"   # borders/dividers sitting on yellow

BG = "#FFEC97"            # soft yellow canvas (minor in this layout)
SURFACE = "#FFFBE6"       # list column, settings body, cards, chips
PAPER = "#FFFEFB"         # reader/document background (warm near-white)
CARD = "#FBEFA6"          # inactive chip / segmented-control track
CARD_HOVER = "#F5E795"
BORDER = "#EFDD83"        # hairline borders on light surfaces
BORDER_DEEP = "#E4CE72"   # stronger hairline (checkbox outline etc.)
SOFT = "#FFE05C"          # selection highlight (selected conversation card)
YELLOW_SOFT = SOFT        # back-compat alias

INK = "#1A1A17"           # primary text, the ink/black button
INK_SOFT = "#3A352B"      # body copy, secondary ink
TEXT = INK
MUTED = "#7A7150"         # secondary text (warm)
SUBTLE = "#AC9F6E"        # tertiary / placeholder
WHITE = "#FFFFFF"         # inputs, popovers, icon-button fills

RECORD = "#E5484D"        # recording red (dot, Stop button FILL - graphical, 3:1)
RECORD_HOVER = "#D43A3F"
AMBER = "#B8860B"         # processing / in-progress (dot/icon FILL - graphical)
GREEN = "#1E9E57"         # success / ready / completed steps (dot/icon FILL)

# AA-safe text variants of the status colours. The vivid colours above are for
# fills, dots, and icons (graphical, 3:1 is correct). When the SAME status is set
# as small TEXT, use these darker variants so it clears WCAG AA (4.5:1).
RECORD_TEXT = "#AE363A"   # red text on white/surface/yellow
AMBER_TEXT = "#866108"    # amber text on surface/paper
GREEN_TEXT = "#177B43"    # green text on white/surface/card

# Pre-blended translucents (Tk has no alpha; these are the PRD rgba() values
# composited onto the surface they sit on).
RAIL_PILL = "#FFEB7A"       # rgba(255,255,255,.40) on YELLOW - rail pills
RAIL_PILL_SOFT = "#FFEA6F"  # rgba(255,255,255,.35) on YELLOW - privacy footer
RAIL_ACTIVE = "#FFF09B"     # rgba(255,255,255,.55) on YELLOW - active nav item
RAIL_HOVER = "#FFE659"      # gentle hover on yellow
RAIL_HAIRLINE = "#E7C61F"   # rgba(120,90,20,.18) on YELLOW
INK_WASH = "#AF991E"        # rgba(26,26,23,.35) on YELLOW - disabled record
REC_TINT = "#FDEDDA"        # rgba(229,72,77,.08) on SURFACE - recording card
HOVER_ROW = "#F4F4F3"       # rgba(26,26,23,.05) on WHITE - popover hover
LIST_HOVER = "#FFF2B6"      # card hover on SURFACE
GREEN_SOFT = "#DDF0E4"      # soft green disc behind done-step checks
AMBER_SOFT = "#F6E9C8"      # soft amber chip fill on paper

# Back-compat aliases (older code paths).
ACCENT = INK
ACCENT_HOVER = "#000000"
ACCENT_SOFT = SOFT
PRIMARY = YELLOW
PRIMARY_HOVER = YELLOW_HOVER
PRIMARY_TEXT = INK

# Wordmark tri-tone.
WORDMARK = (INK, "#6B5E3A", INK)

# Keyboard-focus ring. Ink on light fills; flips to yellow on dark (ink) fills so
# the ring stays visible regardless of the control it sits on.
FOCUS = INK
FOCUS_ON_DARK = YELLOW


# --- Spacing / radius / motion scales -----------------------------------
# Named steps so layout uses a shared rhythm instead of scattered magic numbers.
class SPACE:
    """4px base spacing scale (Tk pixels)."""
    XS, SM, MD, LG, XL, XXL = 4, 8, 12, 16, 24, 32


class RADIUS:
    """Editorial-brutalist: corners collapse toward square. Structure comes from
    thick ink rules and slabs, not rounding."""
    SM, MD, LG = 2, 3, 3


# Thick structural rule weight (the brutalist signature divider/border).
RULE = 2


class MOTION:
    """Animation durations in milliseconds. All tweens ease out (no bounce).

    `reduced` mirrors an OS "reduce motion" preference: when True, callers skip
    continuous/decorative animation and snap straight to the end state.
    """
    FAST, BASE, SLOW, PULSE = 120, 200, 320, 1000
    reduced = False


def _detect_reduced_motion():
    """Best-effort read of the OS 'reduce motion' accessibility preference.
    Defaults to False (full motion) if it can't be determined."""
    try:
        if sys.platform == "darwin":
            import subprocess
            out = subprocess.run(
                ["defaults", "read", "com.apple.universalaccess", "reduceMotion"],
                capture_output=True, text=True, timeout=1.5)
            return out.stdout.strip() == "1"
        if os.name == "nt":
            import ctypes
            val = ctypes.c_int(0)
            # SPI_GETCLIENTAREAANIMATION = 0x1042; False means "reduce motion".
            if ctypes.windll.user32.SystemParametersInfoW(
                    0x1042, 0, ctypes.byref(val), 0):
                return val.value == 0
    except Exception:
        pass
    return False


MOTION.reduced = _detect_reduced_motion()

# Discrete palette offered when colour-coding a project. The first is the
# default (matches the old amber swatch).
PROJECT_COLORS = [
    "#B8860B",  # amber (default)
    "#E5484D",  # red
    "#E5793A",  # orange
    "#1E9E57",  # green
    "#2A8FBD",  # blue
    "#5B5BD6",  # indigo
    "#9333A8",  # purple
    "#C2298A",  # pink
]
PROJECT_COLOR_DEFAULT = PROJECT_COLORS[0]


def color_for_project(project):
    """The swatch colour for a project dict. Uses the stored colour, else a
    stable colour derived from the name, else the default."""
    if not project:
        return PROJECT_COLOR_DEFAULT
    c = project.get("color")
    if c:
        return c
    name = (project.get("name") or "").strip()
    if not name:
        return PROJECT_COLOR_DEFAULT
    return PROJECT_COLORS[sum(ord(ch) for ch in name) % len(PROJECT_COLORS)]


# --- Fonts --------------------------------------------------------------
# PRD sizes are px; Tk takes points (px * 0.75 at 96 dpi) - sizes below are pt.
def font(size=10, weight="normal"):
    """Body font (Hanken Grotesk). weight='bold' uses the real 700 face."""
    return (UI_BOLD, size) if weight == "bold" else (UI_FAMILY, size)


def med(size=10):
    return (UI_MED, size)


def semi(size=10):
    return (UI_SEMI, size)


def bold(size=10):
    return (UI_BOLD, size)


def head(size=12, weight=None):
    """Heading font (Bricolage Grotesque, true 700 - never synth-bold it)."""
    return (HEAD_FAMILY, size)


def brand(size=15):
    """Wordmark font (Bricolage Grotesque ExtraBold)."""
    return (BRAND_FAMILY, size)


# Named type ramp: hierarchy through scale + weight contrast, not color. Use
# these instead of raw sizes so a single edit re-tunes the whole app.
class Type:
    HERO = (BRAND_FAMILY, 72)      # the giant recording timer
    NUMERAL = (BRAND_FAMILY, 28)   # big leading index numeral (numbered rows)
    DISPLAY = (BRAND_FAMILY, 26)   # wordmark
    H1 = (HEAD_FAMILY, 30)         # screen titles (big, editorial)
    H2 = (HEAD_FAMILY, 18)         # section headers
    H3 = (UI_SEMI, 13)             # card / row titles
    BODY = (UI_FAMILY, 11)         # default body
    LABEL = (UI_BOLD, 10)          # buttons, controls (bold, often all-caps)
    CAPTION = (UI_FAMILY, 10)      # secondary / metadata
    EYEBROW = (UI_BOLD, 9)         # all-caps tracked eyebrow
    MICRO = (UI_BOLD, 8)           # smallest all-caps label


def hero(size=72):
    """The giant Bricolage ExtraBold timer face."""
    return (BRAND_FAMILY, size)


def numeral(size=28):
    """The big leading index numeral face (Bricolage ExtraBold). Used by the
    numbered ruled rows in the welcome, list and processing views."""
    return (BRAND_FAMILY, size)


def lighten(hexcol, amt):
    """Blend a #rrggbb colour toward white by `amt` (0..1)."""
    return mix(hexcol, "#FFFFFF", amt)


def mix(c1, c2, t):
    """Blend two #rrggbb colours: c1 toward c2 by t (0..1)."""
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    a = tuple(int(c1[i:i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(c2[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def _rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(hexcol):
    """WCAG relative luminance (0..1) of a #rrggbb colour."""
    def chan(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(v) for v in _rgb(hexcol))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(c1, c2):
    """WCAG contrast ratio between two #rrggbb colours (1..21)."""
    l1, l2 = _relative_luminance(c1), _relative_luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def passes_AA(fg, bg, large=False):
    """True if fg-on-bg clears WCAG AA (4.5:1 body, 3:1 large text)."""
    return contrast_ratio(fg, bg) >= (3.0 if large else 4.5)


# Text tokens that must clear AA (4.5:1) on these surfaces (checked by the smoke
# test). SUBTLE is intentionally excluded: it is placeholder/decorative only and
# must never carry information a user needs to read. The raw status colours
# (RECORD/AMBER/GREEN) are excluded here too: they are graphical (fills, dots,
# icons) at the 3:1 non-text bar - use the *_TEXT variants for small text.
CONTRAST_REQUIRED = {
    "INK": (INK, [SURFACE, PAPER, YELLOW, BG]),
    "INK_SOFT": (INK_SOFT, [SURFACE, PAPER, YELLOW, BG]),
    "MUTED": (MUTED, [SURFACE, PAPER]),
    "RECORD_TEXT": (RECORD_TEXT, [WHITE, SURFACE, YELLOW]),
    "AMBER_TEXT": (AMBER_TEXT, [SURFACE, PAPER, AMBER_SOFT]),
    "GREEN_TEXT": (GREEN_TEXT, [WHITE, SURFACE, CARD]),
}

# Status fills used as graphics (dots/icons/bars) must clear the 3:1 non-text bar.
CONTRAST_GRAPHICAL = {
    "RECORD": (RECORD, [WHITE, SURFACE]),
    "GREEN": (GREEN, [SURFACE]),
    "AMBER": (AMBER, [SURFACE, PAPER]),
}


def _rounded_points(x1, y1, x2, y2, r):
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle on a canvas; returns the item id."""
    r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
    return canvas.create_polygon(_rounded_points(x1, y1, x2, y2, r),
                                 smooth=True, **kw)


# --- Editorial-brutalist helpers ----------------------------------------
def rule(parent, bg, color=INK, height=RULE, **pack):
    """A thick horizontal structural rule (the brutalist divider). Packs by
    default with fill='x'; pass pack kwargs to override."""
    f = tk.Frame(parent, bg=color, height=height)
    pack.setdefault("fill", "x")
    f.pack(**pack)
    return f


class Eyebrow(tk.Label):
    """An all-caps, letter-spaced eyebrow label (small bold tracked caps)."""

    def __init__(self, parent, text, bg=PAPER, fg=MUTED, font_=None, **kw):
        spaced = " ".join(text.upper())  # poor-man's tracking (Tk has no kerning)
        super().__init__(parent, text=spaced, bg=bg, fg=fg,
                         font=font_ or Type.EYEBROW, **kw)


class SectionHead(tk.Frame):
    """A bold all-caps section header with a thick ink underline rule below."""

    def __init__(self, parent, text, bg=PAPER, fg=INK, rule_color=INK,
                 font_=None):
        super().__init__(parent, bg=bg)
        tk.Label(self, text=text.upper(), bg=bg, fg=fg,
                 font=font_ or Type.H2, anchor="w").pack(fill="x")
        tk.Frame(self, bg=rule_color, height=RULE).pack(fill="x", pady=(4, 0))


def slab(canvas, x1, y1, x2, y2, fill, outline=INK, width=RULE, r=RADIUS.MD):
    """A near-square block with a thick ink border: the core brutalist surface."""
    return round_rect(canvas, x1, y1, x2, y2, r, fill=fill, outline=outline,
                      width=width)


class NumberedRow(tk.Frame):
    """A numbered, ruled editorial row: a big leading index numeral, a title and
    optional supporting copy, over a thick ink divider. The brutalist
    replacement for soft step cards (welcome steps, processing checklist)."""

    def __init__(self, parent, index, title, desc=None, bg=PAPER, fg=INK,
                 rule_color=INK, numeral_color=INK, desc_color=MUTED,
                 rule_top=True):
        super().__init__(parent, bg=bg)
        if rule_top:
            tk.Frame(self, bg=rule_color, height=RULE).pack(fill="x")
        row = tk.Frame(self, bg=bg)
        row.pack(fill="x", pady=(10, 12))
        self.numeral = tk.Label(row, text=str(index), bg=bg, fg=numeral_color,
                                font=Type.NUMERAL, width=2, anchor="w")
        self.numeral.pack(side="left", padx=(0, 14))
        col = tk.Frame(row, bg=bg)
        col.pack(side="left", fill="x", expand=True)
        self.title = tk.Label(col, text=title.upper(), bg=bg, fg=fg,
                              font=Type.H3, anchor="w")
        self.title.pack(fill="x")
        self.desc = None
        if desc:
            self.desc = tk.Label(col, text=desc, bg=bg, fg=desc_color,
                                 font=Type.BODY, anchor="w", justify="left")
            self.desc.pack(fill="x", pady=(2, 0))


# --- Line icons ---------------------------------------------------------
# 1.7px-stroke style line icons drawn straight onto a canvas. (cx, cy) is the
# centre; s is the icon box size. Round caps/joins, currentColor.
def draw_icon(c, name, cx, cy, s, color, width=1.7):
    w = max(1.4, width * s / 16)
    kw = dict(fill=color, width=w, capstyle="round", joinstyle="round")
    h = s / 2.0

    def L(*pts):
        c.create_line(*[(cx + px * h, cy + py * h) for px, py in
                        zip(pts[::2], pts[1::2])], **kw)

    def O(x1, y1, x2, y2, fill=""):
        c.create_oval(cx + x1 * h, cy + y1 * h, cx + x2 * h, cy + y2 * h,
                      outline=color, width=w, fill=fill)

    if name == "search":
        O(-0.8, -0.8, 0.35, 0.35)
        L(0.38, 0.38, 0.85, 0.85)
    elif name == "home":
        L(-0.85, -0.05, 0, -0.85, 0.85, -0.05)
        L(-0.62, 0.12, -0.62, 0.8, 0.62, 0.8, 0.62, 0.12)
    elif name == "folder":
        L(-0.85, 0.7, -0.85, -0.55, -0.25, -0.55, -0.05, -0.3, 0.85, -0.3,
          0.85, 0.7, -0.85, 0.7)
    elif name == "gear":
        O(-0.32, -0.32, 0.32, 0.32)
        for i in range(8):
            a = i * math.pi / 4
            L(0.55 * math.cos(a), 0.55 * math.sin(a),
              0.85 * math.cos(a), 0.85 * math.sin(a))
    elif name == "mic":
        round_rect(c, cx - 0.28 * h, cy - 0.9 * h, cx + 0.28 * h, cy + 0.15 * h,
                   0.28 * h, fill="", outline=color, width=w)
        c.create_arc(cx - 0.6 * h, cy - 0.55 * h, cx + 0.6 * h, cy + 0.45 * h,
                     start=180, extent=180, style="arc", outline=color, width=w)
        L(0, 0.45, 0, 0.85)
    elif name == "lock":
        round_rect(c, cx - 0.7 * h, cy - 0.15 * h, cx + 0.7 * h, cy + 0.85 * h,
                   0.22 * h, fill="", outline=color, width=w)
        c.create_arc(cx - 0.42 * h, cy - 0.85 * h, cx + 0.42 * h, cy + 0.15 * h,
                     start=0, extent=180, style="arc", outline=color, width=w)
    elif name == "copy":
        round_rect(c, cx - 0.85 * h, cy - 0.85 * h, cx + 0.3 * h, cy + 0.3 * h,
                   0.18 * h, fill="", outline=color, width=w)
        L(-0.3, 0.55, -0.3, 0.72, 0.85, 0.72, 0.85, -0.42, 0.6, -0.42)
    elif name == "share":
        L(0, 0.1, 0, -0.85)
        L(-0.38, -0.5, 0, -0.88, 0.38, -0.5)
        L(-0.8, 0.05, -0.8, 0.8, 0.8, 0.8, 0.8, 0.05)
    elif name == "download":
        L(0, -0.85, 0, 0.1)
        L(-0.38, -0.25, 0, 0.13, 0.38, -0.25)
        L(-0.8, 0.5, -0.8, 0.8, 0.8, 0.8, 0.8, 0.5)
    elif name == "chev_down":
        L(-0.5, -0.22, 0, 0.3, 0.5, -0.22)
    elif name == "chev_right":
        L(-0.22, -0.5, 0.3, 0, -0.22, 0.5)
    elif name == "kebab":
        for dy in (-0.62, 0, 0.62):
            c.create_oval(cx - 0.1 * h, cy + (dy - 0.1) * h,
                          cx + 0.1 * h, cy + (dy + 0.1) * h,
                          fill=color, outline=color)
    elif name == "sparkle":
        p = []
        for i in range(8):
            a = i * math.pi / 4 - math.pi / 2
            r = h * (0.95 if i % 2 == 0 else 0.3)
            p += [cx + r * math.cos(a), cy + r * math.sin(a)]
        c.create_polygon(p, smooth=False, fill=color, outline=color, width=1)
    elif name == "refresh":
        # A circular arrow (regenerate / override): a near-full arc with a small
        # arrowhead at the opening on the upper right.
        c.create_arc(cx - 0.72 * h, cy - 0.72 * h, cx + 0.72 * h, cy + 0.72 * h,
                     start=60, extent=280, style="arc", outline=color, width=w)
        L(0.36, -0.62, 0.74, -0.46, 0.54, -0.04)
    elif name == "check":
        L(-0.6, 0.05, -0.15, 0.5, 0.65, -0.45)
    elif name == "plus":
        L(0, -0.7, 0, 0.7)
        L(-0.7, 0, 0.7, 0)
    elif name == "dot":
        c.create_oval(cx - 0.42 * h, cy - 0.42 * h, cx + 0.42 * h, cy + 0.42 * h,
                      fill=color, outline=color)
    elif name == "square":
        round_rect(c, cx - 0.42 * h, cy - 0.42 * h, cx + 0.42 * h, cy + 0.42 * h,
                   0.16 * h, fill=color, outline=color)
    elif name == "stop":
        round_rect(c, cx - 0.5 * h, cy - 0.5 * h, cx + 0.5 * h, cy + 0.5 * h,
                   0.2 * h, fill=color, outline=color)


class Icon(tk.Canvas):
    """A small canvas that renders one line icon."""

    def __init__(self, parent, name, size=16, color=INK_SOFT, bg=SURFACE,
                 stroke=1.7):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0)
        self._args = (name, size, color, stroke)
        self.redraw()

    def redraw(self, color=None, bg=None):
        name, size, col, stroke = self._args
        if color:
            col = color
            self._args = (name, size, col, stroke)
        if bg:
            self.configure(bg=bg)
        self.delete("all")
        draw_icon(self, name, size / 2, size / 2, size * 0.82, col, stroke)


# --- Buttons ------------------------------------------------------------
class RoundedButton(tk.Canvas):
    """A rounded button: optional leading icon, optional darker bottom "lip",
    optional fixed width. Hover + disabled states stay on-brand."""

    def __init__(self, parent, text, command=None, fill=PRIMARY,
                 fill_hover=PRIMARY_HOVER, fg=PRIMARY_TEXT, bg=BG, font_=None,
                 padx=20, pady=11, radius=12, border=None, icon=None,
                 icon_color=None, lip=None, min_width=None, border_width=1.4,
                 caps=False, lip_h=2):
        self._fill = fill
        self._fill_hover = fill_hover
        self._fg = fg
        self._radius = radius
        self._border = border
        self._border_width = border_width
        self._caps = caps
        self._lip_h = lip_h
        self._command = command
        self._font = font_ or semi(10)
        self._icon = icon
        self._icon_color = icon_color
        self._lip = lip
        self._padx, self._pady = padx, pady
        self._min_width = min_width
        self._enabled = True
        self._hovered = False
        self._focused = False
        self._text = text

        super().__init__(parent, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2", takefocus=1)
        self._measure()
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_focus_click)
        # Keyboard a11y: focus ring + Return/Space activation.
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_click)
        self.bind("<KP_Enter>", self._on_click)
        self.bind("<space>", self._on_click)

    def _display(self):
        return self._text.upper() if self._caps else self._text

    def _measure(self):
        f = tkfont.Font(family=self._font[0], size=self._font[1])
        tw = f.measure(self._display())
        th = f.metrics("linespace")
        self._iw = th * 0.62 if self._icon else 0
        gap = 8 if self._icon else 0
        w = tw + self._iw + gap + self._padx * 2
        if self._min_width:
            w = max(w, self._min_width)
        h = th + self._pady * 2 + (self._lip_h if self._lip else 0)
        self._cw, self._ch = int(w), int(h)
        self.configure(width=self._cw, height=self._ch)
        self._tw, self._gap = tw, gap

    def _draw(self):
        self.delete("all")
        fill = self._fill_hover if (self._hovered and self._enabled) else self._fill
        fg = self._fg
        if not self._enabled:
            fill = lighten(self._fill, 0.6)
            fg = mix(self._fg, fill, 0.45)
        bh = self._ch - (self._lip_h if self._lip else 0)
        if self._lip and self._enabled:
            round_rect(self, 1, 1 + self._lip_h, self._cw - 1, self._ch - 1,
                       self._radius, fill=self._lip, outline=self._lip)
        outline = self._border or fill
        width = self._border_width
        if self._focused and self._enabled:
            # Visible focus ring: contrast against the fill (yellow on dark fills).
            outline = FOCUS_ON_DARK if _relative_luminance(fill) < 0.4 else FOCUS
            width = max(2.2, self._border_width)
        round_rect(self, 1, 1, self._cw - 1, bh - 1, self._radius,
                   fill=fill, outline=outline, width=width)
        x = (self._cw - self._tw - self._iw - self._gap) / 2
        cy = bh / 2
        if self._icon:
            ic = self._icon_color or fg
            if not self._enabled:
                ic = mix(ic, fill, 0.45)
            draw_icon(self, self._icon, x + self._iw / 2, cy, self._iw, ic)
            x += self._iw + self._gap
        self.create_text(x, cy, text=self._display(), fill=fg, font=self._font,
                         anchor="w")

    def _on_enter(self, _e):
        self._hovered = True
        if self._enabled:
            self._draw()

    def _on_leave(self, _e):
        self._hovered = False
        if self._enabled:
            self._draw()

    def _on_focus_click(self, _e):
        # Pointer press also takes keyboard focus, then activates.
        if self._enabled:
            self.focus_set()
        self._on_click(_e)

    def _on_click(self, _e):
        if self._command and self._enabled:
            self._command()

    def _on_focus_in(self, _e):
        self._focused = True
        self._draw()

    def _on_focus_out(self, _e):
        self._focused = False
        self._draw()

    def set_text(self, text):
        self._text = text
        self._measure()
        self._draw()

    def set_colors(self, fill, fill_hover, fg=None, icon=None, icon_color=None,
                   lip="keep"):
        self._fill, self._fill_hover = fill, fill_hover
        if fg:
            self._fg = fg
        if icon is not None:
            self._icon = icon or None
        if icon_color is not None:
            self._icon_color = icon_color
        if lip != "keep":
            self._lip = lip
        self._measure()
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()


class IconButton(tk.Canvas):
    """A small rounded-square button with a line icon (copy / share / etc.)."""

    def __init__(self, parent, name, command=None, size=32, bg=PAPER,
                 fill=WHITE, border=INK, color=INK, tooltip=None):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2",
                         takefocus=1)
        self._name, self._size = name, size
        self._fill, self._border, self._color = fill, border, color
        self._command = command
        self._hover = False
        self._focused = False
        self._draw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._click)
        # Keyboard a11y: focus ring + Return/Space activation.
        self.bind("<FocusIn>", lambda e: self._set_focused(True))
        self.bind("<FocusOut>", lambda e: self._set_focused(False))
        self.bind("<Return>", lambda e: self._activate())
        self.bind("<KP_Enter>", lambda e: self._activate())
        self.bind("<space>", lambda e: self._activate())

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    def _set_focused(self, on):
        self._focused = on
        self._draw()

    def _click(self, _e):
        self.focus_set()
        self._activate()

    def _activate(self):
        if self._command:
            self._command()

    def _draw(self):
        self.delete("all")
        s = self._size
        fill = YELLOW if self._hover else self._fill
        outline = FOCUS if self._focused else self._border
        width = 2.4 if self._focused else RULE
        round_rect(self, 1, 1, s - 1, s - 1, RADIUS.SM, fill=fill,
                   outline=outline, width=width)
        draw_icon(self, self._name, s / 2, s / 2, s * 0.5, self._color)


class SegmentedTabs(tk.Canvas):
    """The [NOTES | TRANSCRIPT] hard toggle: squared, ink-bordered, all-caps,
    with an ink-slab active segment (yellow text)."""

    PAD_X = 18
    PAD_Y = 7

    def __init__(self, parent, tabs, command=None, bg=PAPER, font_=None):
        self._tabs = list(tabs)          # [(key, label)]
        self._active = tabs[0][0] if tabs else None
        self._command = command
        self._font = font_ or bold(9)
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self._layout()
        self.bind("<Button-1>", self._click)

    def set_tabs(self, tabs, active=None):
        self._tabs = list(tabs)
        if active is not None:
            self._active = active
        elif self._tabs and self._active not in [k for k, _ in self._tabs]:
            self._active = self._tabs[0][0]
        self._layout()

    def set_active(self, key):
        self._active = key
        self._layout()

    def _layout(self):
        f = tkfont.Font(family=self._font[0], size=self._font[1])
        th = f.metrics("linespace")
        h = th + self.PAD_Y * 2 + 6
        self._zones = []
        x = 4
        widths = []
        for key, label in self._tabs:
            w = f.measure(label) + self.PAD_X * 2
            widths.append(w)
            x += w
        total = sum(widths) + 8
        self.configure(width=total, height=h)
        self.delete("all")
        round_rect(self, 1, 1, total - 1, h - 1, RADIUS.SM, fill=WHITE,
                   outline=INK, width=RULE)
        x = 4
        for (key, label), w in zip(self._tabs, widths):
            active = key == self._active
            if active:
                round_rect(self, x, 4, x + w, h - 4, RADIUS.SM, fill=INK,
                           outline=INK, width=RULE)
            self.create_text(x + w / 2, h / 2, text=label.upper(),
                             fill=YELLOW if active else INK, font=self._font)
            self._zones.append((x, x + w, key))
            x += w

    def _click(self, e):
        for x1, x2, key in self._zones:
            if x1 <= e.x <= x2 and key != self._active:
                self._active = key
                self._layout()
                if self._command:
                    self._command(key)
                break


# --- Containers ---------------------------------------------------------
class ScrollFrame(tk.Frame):
    """A vertically scrollable container. Put your widgets in `.body`."""

    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scrollset)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>",
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _on_scrollset(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.vsb.pack_forget()
        else:
            self.vsb.pack(side="right", fill="y")
        self.vsb.set(lo, hi)

    def _wheel(self, e):
        self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def to_top(self):
        self.canvas.yview_moveto(0.0)


# --- Popover menu -------------------------------------------------------
class Popover(tk.Toplevel):
    """A white rounded popover menu: items with hover, separators, section
    labels, a leading selection dot, and red 'danger' items."""

    def __init__(self, parent, min_width=200):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=INK)  # 1px ink-ish frame doubles as a soft shadow line
        self.attributes("-topmost", True)
        self._inner = tk.Frame(self, bg=WHITE)
        self._inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._pad = tk.Frame(self._inner, bg=WHITE)
        self._pad.pack(fill="both", expand=True, padx=5, pady=5)
        self._min_width = min_width
        self.withdraw()
        self.bind("<Escape>", lambda e: self.close())
        self.bind("<FocusOut>", lambda e: self.close())

    def label(self, text):
        tk.Label(self._pad, text=text.upper(), bg=WHITE, fg=SUBTLE,
                 font=bold(7), anchor="w", padx=9, pady=2).pack(fill="x")

    def item(self, text, command, selected=None, danger=False, swatch=None):
        fg = RECORD if danger else INK_SOFT
        hover = "#FBEAEA" if danger else HOVER_ROW
        row = tk.Frame(self._pad, bg=WHITE, cursor="hand2")
        row.pack(fill="x")
        lead = tk.Canvas(row, width=16, height=16, bg=WHITE,
                         highlightthickness=0, bd=0)
        lead.pack(side="left", padx=(9, 2), pady=6)
        if selected:
            lead.create_oval(5, 5, 11, 11, fill=INK, outline=INK)
        elif swatch:
            round_rect(lead, 4, 4, 12, 12, 2, fill=swatch, outline=swatch)
        lbl = tk.Label(row, text=text, bg=WHITE, fg=fg, font=med(10),
                       anchor="w", padx=2, pady=5)
        lbl.pack(side="left", fill="x", expand=True)

        def on(_e=None):
            for w in (row, lead, lbl):
                w.configure(bg=hover)

        def off(_e=None):
            for w in (row, lead, lbl):
                w.configure(bg=WHITE)

        def click(_e=None):
            self.close()
            command()
        for w in (row, lead, lbl):
            w.bind("<Enter>", on)
            w.bind("<Leave>", off)
            w.bind("<Button-1>", click)

    def separator(self):
        tk.Frame(self._pad, bg=BORDER, height=1).pack(fill="x", padx=6, pady=4)

    def open(self, x, y):
        self.update_idletasks()
        w = max(self._min_width, self._pad.winfo_reqwidth() + 12)
        h = self._pad.winfo_reqheight() + 12
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = min(x, sw - w - 8)
        y = min(y, sh - h - 8)
        self.geometry(f"{w}x{h}+{int(x)}+{int(y)}")
        self.deiconify()
        self.lift()
        self.focus_force()
        # Close when clicking anywhere outside.
        self.bind_all("<Button-1>", self._maybe_close, add="+")

    def _maybe_close(self, e):
        if not str(e.widget).startswith(str(self)):
            self.close()

    def close(self):
        try:
            self.unbind_all("<Button-1>")
            self.destroy()
        except tk.TclError:
            pass


# --- Fields -------------------------------------------------------------
class SearchField(tk.Frame):
    """A white rounded-ish search input with a leading search icon."""

    def __init__(self, parent, placeholder="Search", on_change=None, bg=SURFACE):
        super().__init__(parent, bg=WHITE, highlightbackground=INK,
                         highlightcolor=INK, highlightthickness=RULE)
        self._placeholder = placeholder
        self._on_change = on_change
        Icon(self, "search", size=15, color=SUBTLE, bg=WHITE).pack(
            side="left", padx=(10, 4), pady=8)
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, font=font(10),
                              bg=WHITE, fg=INK, relief="flat", bd=0,
                              insertbackground=INK, highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=7)
        self._ph = tk.Label(self, text=placeholder, bg=WHITE, fg=SUBTLE,
                            font=font(10))
        self._ph.place(in_=self.entry, x=1, y=1)
        self._ph.bind("<Button-1>", lambda e: self.entry.focus_set())
        self.var.trace_add("write", self._changed)

    def _changed(self, *_):
        text = self.var.get()
        if text:
            self._ph.place_forget()
        else:
            self._ph.place(in_=self.entry, x=1, y=1)
        if self._on_change:
            self._on_change(text)


def entry(parent, var, width=None, bg=WHITE):
    """The shared field style: white, hairline border, ink focus ring."""
    e = tk.Entry(parent, textvariable=var, font=font(10), bg=bg, fg=INK,
                 relief="flat", insertbackground=INK, highlightthickness=RULE,
                 highlightbackground=INK, highlightcolor=INK, bd=7)
    if width:
        e.configure(width=width)
    return e


# --- Button factories (editorial-brutalist slabs) -----------------------
def AccentButton(parent, text, command, bg=BG, icon=None, lip=True):
    """Primary action: a yellow slab, all-caps ink label, 2px ink border, deep
    ink bottom lip. The signature brutalist control."""
    return RoundedButton(parent, text, command, fill=PRIMARY,
                         fill_hover=PRIMARY_HOVER, fg=INK, bg=bg,
                         font_=bold(10), padx=20, pady=11, radius=RADIUS.MD,
                         icon=icon, border=INK, border_width=RULE, caps=True,
                         lip=INK if lip else None, lip_h=3)


def InkButton(parent, text, command, bg=BG, icon=None):
    """Strong secondary: an ink slab with a yellow all-caps label."""
    return RoundedButton(parent, text, command, fill=INK, fill_hover="#33312B",
                         fg=YELLOW, bg=bg, font_=bold(10), padx=20, pady=11,
                         radius=RADIUS.MD, icon=icon, border=INK,
                         border_width=RULE, caps=True)


def GhostButton(parent, text, command, bg=BG, icon=None):
    """Quiet action: white slab with a 2px ink border, all-caps ink label."""
    return RoundedButton(parent, text, command, fill=WHITE, fill_hover=SURFACE,
                         fg=INK, bg=bg, border=INK, border_width=RULE,
                         font_=bold(9), padx=16, pady=9, radius=RADIUS.SM,
                         icon=icon, caps=True)


def BarButton(parent, text, command, bg=BG, icon=None, fill=PRIMARY,
              fg=INK, min_width=240):
    """A full-width primary bar: big all-caps label, ink border, deep lip.
    Use for the dominant call-to-action on a screen."""
    return RoundedButton(parent, text, command, fill=fill,
                         fill_hover=PRIMARY_HOVER if fill == PRIMARY else "#33312B",
                         fg=fg, bg=bg, font_=bold(11), padx=22, pady=13,
                         radius=RADIUS.MD, icon=icon, border=INK,
                         border_width=RULE, caps=True, lip=INK, lip_h=3,
                         min_width=min_width)
