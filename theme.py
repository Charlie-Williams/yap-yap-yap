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
import glob
import math
import tkinter as tk
import tkinter.font as tkfont


# --- Bundled fonts ------------------------------------------------------
def _load_bundled_fonts():
    if os.name != "nt":
        return
    import ctypes
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")
    try:
        for ttf in glob.glob(os.path.join(d, "*.ttf")):
            ctypes.windll.gdi32.AddFontResourceExW(ctypes.c_wchar_p(ttf), 0x10, 0)
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

RECORD = "#E5484D"        # recording red (dot, Stop button)
RECORD_HOVER = "#D43A3F"
AMBER = "#B8860B"         # processing / in-progress
GREEN = "#1E9E57"         # success / ready / completed steps

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


def lighten(hexcol, amt):
    """Blend a #rrggbb colour toward white by `amt` (0..1)."""
    return mix(hexcol, "#FFFFFF", amt)


def mix(c1, c2, t):
    """Blend two #rrggbb colours: c1 toward c2 by t (0..1)."""
    c1, c2 = c1.lstrip("#"), c2.lstrip("#")
    a = tuple(int(c1[i:i + 2], 16) for i in (0, 2, 4))
    b = tuple(int(c2[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


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
                 icon_color=None, lip=None, min_width=None):
        self._fill = fill
        self._fill_hover = fill_hover
        self._fg = fg
        self._radius = radius
        self._border = border
        self._command = command
        self._font = font_ or semi(10)
        self._icon = icon
        self._icon_color = icon_color
        self._lip = lip
        self._padx, self._pady = padx, pady
        self._min_width = min_width
        self._enabled = True
        self._hovered = False
        self._text = text

        super().__init__(parent, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        self._measure()
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _measure(self):
        f = tkfont.Font(family=self._font[0], size=self._font[1])
        tw = f.measure(self._text)
        th = f.metrics("linespace")
        self._iw = th * 0.62 if self._icon else 0
        gap = 8 if self._icon else 0
        w = tw + self._iw + gap + self._padx * 2
        if self._min_width:
            w = max(w, self._min_width)
        h = th + self._pady * 2 + (2 if self._lip else 0)
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
        bh = self._ch - (2 if self._lip else 0)
        if self._lip and self._enabled:
            round_rect(self, 1, 3, self._cw - 1, self._ch - 1, self._radius,
                       fill=self._lip, outline=self._lip)
        outline = self._border or fill
        round_rect(self, 1, 1, self._cw - 1, bh - 1, self._radius,
                   fill=fill, outline=outline, width=1.4)
        x = (self._cw - self._tw - self._iw - self._gap) / 2
        cy = bh / 2
        if self._icon:
            ic = self._icon_color or fg
            if not self._enabled:
                ic = mix(ic, fill, 0.45)
            draw_icon(self, self._icon, x + self._iw / 2, cy, self._iw, ic)
            x += self._iw + self._gap
        self.create_text(x, cy, text=self._text, fill=fg, font=self._font,
                         anchor="w")

    def _on_enter(self, _e):
        self._hovered = True
        if self._enabled:
            self._draw()

    def _on_leave(self, _e):
        self._hovered = False
        if self._enabled:
            self._draw()

    def _on_click(self, _e):
        if self._command and self._enabled:
            self._command()

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

    def __init__(self, parent, name, command=None, size=30, bg=PAPER,
                 fill=WHITE, border=BORDER, color=INK_SOFT, tooltip=None):
        super().__init__(parent, width=size, height=size, bg=bg,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._name, self._size = name, size
        self._fill, self._border, self._color = fill, border, color
        self._command = command
        self._hover = False
        self._draw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._command and self._command())

    def _set_hover(self, on):
        self._hover = on
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        fill = mix(self._fill, CARD, 0.5) if self._hover else self._fill
        round_rect(self, 1, 1, s - 1, s - 1, 9, fill=fill,
                   outline=self._border, width=1.2)
        draw_icon(self, self._name, s / 2, s / 2, s * 0.5, self._color)


class SegmentedTabs(tk.Canvas):
    """The [Notes | Transcript] segmented pill control."""

    PAD_X = 16
    PAD_Y = 5

    def __init__(self, parent, tabs, command=None, bg=PAPER, font_=None):
        self._tabs = list(tabs)          # [(key, label)]
        self._active = tabs[0][0] if tabs else None
        self._command = command
        self._font = font_ or semi(10)
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
        round_rect(self, 0, 0, total, h, h / 2, fill=CARD, outline=BORDER,
                   width=1.2)
        x = 4
        for (key, label), w in zip(self._tabs, widths):
            active = key == self._active
            if active:
                round_rect(self, x, 4, x + w, h - 4, (h - 8) / 2, fill=WHITE,
                           outline=BORDER, width=1)
            self.create_text(x + w / 2, h / 2, text=label,
                             fill=INK if active else MUTED, font=self._font)
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
        super().__init__(parent, bg=WHITE, highlightbackground=BORDER,
                         highlightcolor=BORDER_DEEP, highlightthickness=1)
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
                 relief="flat", insertbackground=INK, highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=INK, bd=7)
    if width:
        e.configure(width=width)
    return e


# --- Button factories ---------------------------------------------------
def AccentButton(parent, text, command, bg=BG, icon=None, lip=True):
    """Primary action - yellow with ink text (and the darker bottom lip)."""
    return RoundedButton(parent, text, command, fill=PRIMARY,
                         fill_hover=PRIMARY_HOVER, fg=PRIMARY_TEXT, bg=bg,
                         font_=semi(10), padx=18, pady=9, radius=11, icon=icon,
                         lip=YELLOW_DEEP if lip else None)


def InkButton(parent, text, command, bg=BG, icon=None):
    """Secondary strong action - ink with white text."""
    return RoundedButton(parent, text, command, fill=INK, fill_hover="#33312B",
                         fg="white", bg=bg, font_=semi(10), padx=18, pady=9,
                         radius=11, icon=icon)


def GhostButton(parent, text, command, bg=BG, icon=None):
    """Quiet action - white with a hairline border."""
    return RoundedButton(parent, text, command, fill=WHITE, fill_hover=SURFACE,
                         fg=INK_SOFT, bg=bg, border=BORDER, font_=semi(9),
                         padx=14, pady=8, radius=10, icon=icon)
