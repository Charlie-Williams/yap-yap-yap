"""
gui.py
------
The main YapYapYap window ("workspace rail" layout). Run it with:

    python gui.py

  - A yellow rail on the left holds the brand, the record control, the project
    picker, navigation (All conversations / Projects / Settings) and the
    privacy footer.
  - A list column shows every conversation, with search and sort.
  - The reader pane on the right shows the notes / transcript of the selected
    conversation, and turns into a live view while recording, transcribing or
    generating notes.

This process NEVER loads the audio-capture or speech-to-text native libraries;
that all happens in worker subprocesses (engine.py). That isolation is what
makes Stop reliable instead of crashing.
"""

import os
import re
import time
import threading
import subprocess
import wave
from datetime import datetime

import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, simpledialog

from yapyapyap import config
from yapyapyap import applog
from yapyapyap.core import engine
from yapyapyap.core import summarize
from yapyapyap.managers import ollama_manager as om
from yapyapyap.managers import whisper_manager as wm
from yapyapyap.ui import floating
from yapyapyap.ui import theme as T
from yapyapyap.ui.settings_window import SettingsWindow

log = applog.setup()

NO_PROJECT = "(No project)"
_ASSETS = config.ASSETS_DIR

RAIL_W = 252
LIST_W = 304
RAIL_INNER = RAIL_W - 32  # rail content width (16px side padding)


def _date_str(stamp):
    try:
        dt = datetime.strptime(stamp, "%Y-%m-%d_%H-%M-%S")
        return dt.strftime("%b %d, %Y · %I:%M %p").replace(" 0", " ")
    except ValueError:
        return stamp


def _rel_date_str(stamp):
    """A compact, friendly date for list cards: 'Today · 1:31 PM'."""
    try:
        dt = datetime.strptime(stamp, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return stamp
    days = (datetime.now().date() - dt.date()).days
    if days == 0:
        day = "Today"
    elif days == 1:
        day = "Yesterday"
    elif 1 < days < 7:
        day = dt.strftime("%a")
    else:
        day = dt.strftime("%b %d").replace(" 0", " ")
    return day + dt.strftime(" · %I:%M %p").replace(" 0", " ")


def _wav_duration(path):
    """Length of a saved .wav in seconds (read from the header; fast)."""
    try:
        with wave.open(path, "rb") as wf:
            rate = wf.getframerate()
            return wf.getnframes() / rate if rate else 0
    except (OSError, wave.Error, EOFError):
        return 0


def _fmt_duration(secs):
    secs = int(round(secs))
    if secs <= 0:
        return ""
    m, s = divmod(secs, 60)
    if m >= 60:
        h, m = divmod(m, 60)
        return f"{h}h {m}m"
    return f"{m}m {s:02d}s" if m else f"{s}s"


def scan_conversations():
    """Return [dict(base, title, date, project, duration, ...)] newest first."""
    folder = config.RECORDINGS_DIR
    if not os.path.isdir(folder):
        return []
    bases = set()
    for f in os.listdir(folder):
        if not f.startswith("meeting_"):
            continue
        if f.endswith(".mic.wav") or f.endswith(".sys.wav"):
            continue  # interim stems, not conversations
        base = f
        for suffix in ("_transcript.txt", "_notes.md", "_title.txt", ".wav"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        bases.add(os.path.join(folder, base))

    items = []
    for b in bases:
        if os.path.exists(b + ".hidden"):
            continue  # hidden from the list (kept on disk)
        stamp, tag = engine.parse_base(b)
        title = None
        try:
            with open(b + "_title.txt", encoding="utf-8") as f:
                title = f.read().strip() or None
        except OSError:
            pass
        items.append({
            "base": b,
            "stamp": stamp,
            "title": title,
            "date": _date_str(stamp),
            "list_date": _rel_date_str(stamp),
            "project": tag or None,
            "duration": _fmt_duration(_wav_duration(b + ".wav")),
            "has_tx": os.path.exists(b + "_transcript.txt"),
            "has_notes": os.path.exists(b + "_notes.md"),
        })
    items.sort(key=lambda d: d["stamp"], reverse=True)
    return items


def _ellipsize(font_obj, text, max_w):
    if font_obj.measure(text) <= max_w:
        return text
    while text and font_obj.measure(text + "…") > max_w:
        text = text[:-1]
    return text + "…"


# ===========================================================================
# Rail / list widgets
# ===========================================================================
class NavItem(tk.Canvas):
    """A rail navigation row: icon + label, rounded highlight when active."""

    H = 34

    def __init__(self, parent, icon, label, command, indent=0, swatch=None,
                 chevron=None, width=RAIL_INNER):
        super().__init__(parent, width=width, height=self.H, bg=T.YELLOW,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._icon, self._label, self._command = icon, label, command
        self._indent, self._swatch, self._chevron = indent, swatch, chevron
        self._wd = width
        self.active = False
        self._hover = False
        self.redraw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._command and self._command())

    def _set_hover(self, on):
        self._hover = on
        self.redraw()

    def set_active(self, on):
        self.active = on
        self.redraw()

    def set_chevron(self, direction):
        self._chevron = direction
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self._wd, self.H
        if self.active:
            T.round_rect(self, 0, 1, w, h - 1, 10, fill=T.RAIL_ACTIVE,
                         outline=T.RAIL_HAIRLINE, width=1)
        elif self._hover:
            T.round_rect(self, 0, 1, w, h - 1, 10, fill=T.RAIL_HOVER,
                         outline=T.RAIL_HOVER)
        x = 14 + self._indent
        if self._swatch:
            T.round_rect(self, x, h / 2 - 4, x + 8, h / 2 + 4, 2,
                         fill=self._swatch, outline=self._swatch)
            x += 18
        elif self._icon:
            T.draw_icon(self, self._icon, x + 8, h / 2, 15, T.INK)
            x += 24
        f = T.semi(10) if not self._indent else T.semi(9)
        self.create_text(x, h / 2, text=self._label, anchor="w", fill=T.INK,
                         font=f)
        if self._chevron:
            T.draw_icon(self, "chev_down" if self._chevron == "down"
                        else "chev_right", w - 16, h / 2, 11, T.INK_SOFT)


class RailPill(tk.Canvas):
    """The project-picker pill that sits in the rail."""

    H = 36

    def __init__(self, parent, on_open, width=RAIL_INNER):
        super().__init__(parent, width=width, height=self.H, bg=T.YELLOW,
                         highlightthickness=0, bd=0, cursor="hand2")
        self._wd = width
        self._on_open = on_open
        self._value = "No project"
        self._has_project = False
        self._hover = False
        self.redraw()
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", lambda e: self._on_open())

    def _set_hover(self, on):
        self._hover = on
        self.redraw()

    def set_value(self, value, has_project):
        self._value = value
        self._has_project = has_project
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self._wd, self.H
        fill = T.RAIL_ACTIVE if self._hover else T.RAIL_PILL
        T.round_rect(self, 0, 1, w, h - 1, 11, fill=fill,
                     outline=T.RAIL_HAIRLINE, width=1)
        sw = T.AMBER if self._has_project else T.SUBTLE
        T.round_rect(self, 14, h / 2 - 4, 22, h / 2 + 4, 2, fill=sw, outline=sw)
        f = tkfont.Font(family=T.UI_MED, size=10)
        label = _ellipsize(f, self._value, w - 64)
        self.create_text(32, h / 2, text=label, anchor="w",
                         fill=T.INK if self._has_project else T.INK_SOFT,
                         font=T.med(10))
        T.draw_icon(self, "chev_down", w - 18, h / 2, 11, T.INK_SOFT)


class PrivacyFooter(tk.Canvas):
    """The little 'Everything stays on this PC' card at the rail's bottom."""

    H = 44

    def __init__(self, parent, width=RAIL_INNER):
        super().__init__(parent, width=width, height=self.H, bg=T.YELLOW,
                         highlightthickness=0, bd=0)
        T.round_rect(self, 0, 1, width, self.H - 1, 12, fill=T.RAIL_PILL_SOFT,
                     outline=T.RAIL_HAIRLINE, width=1)
        T.draw_icon(self, "lock", 22, self.H / 2, 14, T.INK_SOFT)
        self.create_text(38, self.H / 2, text="Everything stays on this PC",
                         anchor="w", fill=T.INK_SOFT, font=T.semi(9))


class ConvCard(tk.Canvas):
    """One conversation in the list column (rounded selection, kebab menu)."""

    H = 76

    def __init__(self, parent, item, on_select, on_menu):
        super().__init__(parent, height=self.H, bg=T.SURFACE,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.item = item
        self._on_select, self._on_menu = on_select, on_menu
        self.selected = False
        self._hover = False
        self._kebab_zone = (0, 0, 0, 0)
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self.bind("<Button-1>", self._click)

    def _set_hover(self, on):
        self._hover = on
        self.redraw()

    def set_selected(self, on):
        self.selected = on
        self.redraw()

    def _click(self, e):
        x1, y1, x2, y2 = self._kebab_zone
        if x1 <= e.x <= x2 and y1 <= e.y <= y2:
            self._on_menu(self.item["base"], e)
        else:
            self._on_select(self.item["base"])

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.H
        if w < 40:
            return
        if self.selected:
            T.round_rect(self, 2, 2, w - 2, h - 4, 12, fill=T.SOFT,
                         outline=T.YELLOW_DEEP, width=1.2)
        elif self._hover:
            T.round_rect(self, 2, 2, w - 2, h - 4, 12, fill=T.LIST_HOVER,
                         outline=T.LIST_HOVER)
        it = self.item
        pad = 14
        f_title = tkfont.Font(family=T.UI_SEMI, size=11)
        title = it["title"] or ("Transcript" if it["has_tx"] else "Recording")
        self.create_text(pad, 21, text=_ellipsize(f_title, title, w - 52),
                         anchor="w", fill=T.INK, font=T.semi(11))
        meta = it["list_date"] + (f"   •   {it['duration']}" if it["duration"]
                                  else "")
        f_meta = tkfont.Font(family=T.UI_MED, size=9)
        self.create_text(pad, 41, text=_ellipsize(f_meta, meta, w - 30),
                         anchor="w", fill=T.MUTED, font=T.med(9))
        x = pad
        if it["project"]:
            T.round_rect(self, x, 56, x + 7, 63, 2, fill=T.AMBER, outline=T.AMBER)
            x += 12
            self.create_text(x, 60, text=it["project"], anchor="w",
                             fill=T.AMBER, font=T.semi(9))
            x += tkfont.Font(family=T.UI_SEMI, size=9).measure(it["project"]) + 14
        else:
            self.create_text(x, 60, text="No project", anchor="w",
                             fill=T.SUBTLE, font=T.med(9))
            x += tkfont.Font(family=T.UI_MED, size=9).measure("No project") + 14
        if it["has_tx"] and not it["has_notes"]:
            self.create_text(x, 60, text="TRANSCRIPT ONLY", anchor="w",
                             fill=T.SUBTLE, font=T.bold(7))
        # Kebab (top-right).
        kx, ky = w - 18, 18
        if self._hover or self.selected:
            T.draw_icon(self, "kebab", kx, ky, 13,
                        T.INK_SOFT if self._hover else T.MUTED)
        self._kebab_zone = (kx - 12, ky - 12, kx + 12, ky + 12)


class RecordingCard(tk.Canvas):
    """The special top-of-list card shown while a recording is in progress."""

    H = 60

    def __init__(self, parent, project_label):
        super().__init__(parent, height=self.H, bg=T.SURFACE,
                         highlightthickness=0, bd=0)
        self._project = project_label
        self._time = "00:00"
        self._pulse = True
        self.bind("<Configure>", lambda e: self.redraw())

    def set_time(self, t, pulse):
        self._time, self._pulse = t, pulse
        self.redraw()

    def redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.H
        if w < 40:
            return
        edge = T.mix(T.RECORD, "#FFFFFF", 0.6)
        T.round_rect(self, 2, 2, w - 2, h - 4, 12, fill=T.REC_TINT,
                     outline=edge, width=1.2)
        dot = T.RECORD if self._pulse else T.mix(T.RECORD, T.REC_TINT, 0.6)
        self.create_oval(16, 22, 26, 32, fill=dot, outline=dot)
        self.create_text(36, 21, text="Recording…", anchor="w", fill=T.INK,
                         font=T.semi(11))
        self.create_text(36, 41, text=f"{self._time} · {self._project}",
                         anchor="w", fill=T.MUTED, font=T.med(9))


# ===========================================================================
# The app
# ===========================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.session = None
        self.state = "idle"  # idle | starting | recording | processing
        self._generating = False
        self._items = []
        self._items_by_base = {}
        self._rec_started = None
        self._rec_card = None
        self._search = ""
        self._sort_newest = True
        self._nav_filter = None        # None = all, else project name
        self._toast_token = 0
        self._pulse_on = True
        self._state_frame = None
        self._conv_selected = None
        self._current_base = None
        self._view_mode = "notes"

        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)

        root.title(config.APP_NAME)
        root.geometry(config.WINDOW_GEOMETRY or "1080x720")
        root.minsize(960, 620)
        root.configure(bg=T.PAPER)
        try:
            self._icon_img = tk.PhotoImage(file=os.path.join(_ASSETS, "logo_64.png"))
            root.iconphoto(True, self._icon_img)
        except Exception:
            pass

        self._build_ui()
        self._refresh_projects()
        self._restore_selected_project()
        self.refresh_list()
        self._show_placeholder()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Floating recording indicator (shown when minimised mid-recording).
        self.indicator = floating.RecordingIndicator(root, on_click=self._restore_window)
        root.bind("<Unmap>", self._on_unmap)
        root.bind("<Map>", self._on_map)

        # First-run: quietly fetch the smallest models so it works out of the box.
        threading.Thread(target=self._first_run_setup, daemon=True).start()

        # Offer to finish any recording a previous session was interrupted on.
        self._recover_queue = []
        root.after(700, self._check_interrupted)

    # ---- floating recording indicator -------------------------------
    def _on_unmap(self, event):
        if event.widget is self.root:
            self.root.after(120, self._update_indicator)

    def _on_map(self, event):
        if event.widget is self.root:
            self.indicator.hide()

    def _update_indicator(self):
        try:
            minimized = self.root.state() == "iconic"
        except tk.TclError:
            minimized = False
        # Only overlay the floating indicator while actually recording.
        if minimized and self.state == "recording":
            self.indicator.show((229, 72, 77))
        else:
            self.indicator.hide()

    def _restore_window(self):
        self.indicator.hide()
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except tk.TclError:
            pass

    def _first_run_setup(self):
        """On first launch, download the smallest transcription model (and the
        smallest notes model if Ollama is already running) so the app is usable
        immediately. No-ops once something is present."""
        try:
            if not wm.downloaded_sizes():
                self._banner_async("Downloading the Tiny transcription model "
                                   "(one-time)…")
                wm.download("tiny")
                if not wm.is_downloaded(config.WHISPER_MODEL):
                    config.update_settings(whisper_model="tiny")
                self._banner_async(None)
            if om.is_running() and not om.list_installed():
                self._banner_async("Downloading the notes model (one-time)…")
                om.pull_model("llama3.2:1b")
                config.update_settings(summary_model="llama3.2:1b")
                self._banner_async(None)
        except Exception:
            log.exception("First-run model setup failed")
            self._banner_async(None)

    def _banner_async(self, text):
        try:
            self.root.after(0, lambda: self._set_banner(text))
        except tk.TclError:
            pass

    def _set_banner(self, text):
        if text:
            self._banner_lbl.configure(text=text)
            if not self._banner.winfo_ismapped():
                self._banner.pack(fill="x", before=self.topbar)
        else:
            self._banner.pack_forget()

    # ----------------------------------------------------------------- UI
    def _build_ui(self):
        # ===== Rail ====================================================
        rail = tk.Frame(self.root, bg=T.YELLOW, width=RAIL_W)
        rail.pack(side="left", fill="y")
        rail.pack_propagate(False)
        tk.Frame(self.root, bg=T.YELLOW_DEEP, width=1).pack(side="left", fill="y")

        # Brand.
        brandrow = tk.Frame(rail, bg=T.YELLOW)
        brandrow.pack(fill="x", padx=16, pady=(18, 16))
        try:
            self._logo_img = tk.PhotoImage(file=os.path.join(_ASSETS, "logo_32.png"))
            tk.Label(brandrow, image=self._logo_img, bg=T.YELLOW, bd=0).pack(
                side="left", padx=(2, 10))
        except Exception:
            self._logo_img = None
        wordmark = tk.Frame(brandrow, bg=T.YELLOW)
        wordmark.pack(side="left")
        for part, shade in zip(("Yap", "Yap", "Yap"), T.WORDMARK):
            tk.Label(wordmark, text=part, bg=T.YELLOW, fg=shade,
                     font=T.brand(15), padx=0, pady=0, bd=0,
                     highlightthickness=0).pack(side="left")

        # Record control.
        self.btn = T.RoundedButton(
            rail, "Start recording", command=self.on_toggle, fill=T.INK,
            fill_hover="#000000", fg="white", bg=T.YELLOW, font_=T.semi(11),
            padx=18, pady=11, radius=12, icon="dot", icon_color=T.RECORD,
            min_width=RAIL_INNER, lip="#0A0A08")
        self.btn.pack(padx=16)

        # Status sub-line under the record control.
        self._sub = tk.Frame(rail, bg=T.YELLOW, height=22)
        self._sub.pack(fill="x", padx=16, pady=(6, 2))
        self._sub.pack_propagate(False)
        subrow = tk.Frame(self._sub, bg=T.YELLOW)
        subrow.pack(anchor="center")
        self._sub_dotc = tk.Canvas(subrow, width=10, height=10, bg=T.YELLOW,
                                   highlightthickness=0, bd=0)
        self._sub_lbl = tk.Label(subrow, text="", bg=T.YELLOW, fg=T.INK_SOFT,
                                 font=T.semi(9))
        self._sub_state = None  # (text, color, dot, pulse)

        # Cancel control — only shown while recording (see _set_state).
        self.cancel_btn = T.RoundedButton(
            rail, "Cancel recording", command=self._cancel_recording,
            fill=T.YELLOW, fill_hover=T.RAIL_HOVER, fg=T.RECORD, bg=T.YELLOW,
            font_=T.semi(9), padx=14, pady=7, radius=10, border=T.RECORD,
            min_width=RAIL_INNER)

        # Project picker.
        self.project_var = tk.StringVar(value=NO_PROJECT)
        self.project_pill = RailPill(rail, self._open_project_menu)
        self.project_pill.pack(padx=16, pady=(8, 20))

        # Nav.
        self.nav_all = NavItem(rail, "home", "All conversations",
                               lambda: self._set_nav(None))
        self.nav_all.pack(padx=16, pady=1)
        self.nav_projects = NavItem(rail, "folder", "Projects",
                                    self._toggle_projects, chevron="down")
        self.nav_projects.pack(padx=16, pady=1)
        self._projects_open = True
        self._proj_holder = tk.Frame(rail, bg=T.YELLOW)
        self._proj_holder.pack(fill="x", padx=16)
        self._proj_items = {}
        self.nav_settings = NavItem(rail, "gear", "Settings",
                                    self.open_settings)
        self.nav_settings.pack(padx=16, pady=1)

        # Privacy footer pinned to the bottom.
        PrivacyFooter(rail).pack(side="bottom", padx=16, pady=(8, 16))

        # ===== List column =============================================
        listcol = tk.Frame(self.root, bg=T.SURFACE, width=LIST_W)
        listcol.pack(side="left", fill="y")
        listcol.pack_propagate(False)
        tk.Frame(self.root, bg=T.BORDER, width=1).pack(side="left", fill="y")

        head = tk.Frame(listcol, bg=T.SURFACE)
        head.pack(fill="x", padx=16, pady=(20, 0))
        self.list_title = tk.Label(head, text="All conversations",
                                   bg=T.SURFACE, fg=T.INK, font=T.head(13),
                                   anchor="w")
        self.list_title.pack(fill="x")

        self.search = T.SearchField(listcol, "Search conversations",
                                    on_change=self._on_search)
        self.search.pack(fill="x", padx=16, pady=(12, 0))

        countrow = tk.Frame(listcol, bg=T.SURFACE)
        countrow.pack(fill="x", padx=18, pady=(10, 4))
        self.count_lbl = tk.Label(countrow, text="", bg=T.SURFACE, fg=T.SUBTLE,
                                  font=T.font(9), anchor="w")
        self.count_lbl.pack(side="left")
        self.sort_lbl = tk.Label(countrow, text="Newest ▾", bg=T.SURFACE,
                                 fg=T.MUTED, font=T.med(9), cursor="hand2")
        self.sort_lbl.pack(side="right")
        self.sort_lbl.bind("<Button-1>", self._open_sort_menu)

        self.conv_scroll = T.ScrollFrame(listcol, bg=T.SURFACE)
        self.conv_scroll.pack(fill="both", expand=True, padx=(8, 4),
                              pady=(2, 10))
        self._conv_cards = {}
        self._empty_lbl = None

        # ===== Reader pane =============================================
        reader = tk.Frame(self.root, bg=T.PAPER)
        reader.pack(side="left", fill="both", expand=True)

        # First-run download banner (hidden until needed).
        self._banner = tk.Frame(reader, bg=T.AMBER_SOFT)
        self._banner_lbl = tk.Label(self._banner, text="", bg=T.AMBER_SOFT,
                                    fg=T.AMBER, font=T.semi(9), pady=6)
        self._banner_lbl.pack()

        self.topbar = tk.Frame(reader, bg=T.PAPER, height=56)
        self.topbar.pack(fill="x")
        self.topbar.pack_propagate(False)
        self.tabs = T.SegmentedTabs(self.topbar,
                                    [("notes", "Notes"),
                                     ("transcript", "Transcript")],
                                    command=self._set_view_mode, bg=T.PAPER)
        self._icons = tk.Frame(self.topbar, bg=T.PAPER)
        # Regenerate AI notes (only shown for conversations that already have
        # notes). Re-runs generation with the latest prompt, overwriting them.
        self.regen_btn = T.IconButton(self._icons, "refresh",
                                      self.regenerate_ai_notes, bg=T.PAPER,
                                      tooltip="Regenerate notes")
        self.copy_btn = T.IconButton(self._icons, "copy", self._copy_doc,
                                     bg=T.PAPER)
        self.copy_btn.pack(side="left", padx=(0, 8))
        self.share_btn = T.IconButton(self._icons, "share", self._reveal_doc,
                                      bg=T.PAPER)
        self.share_btn.pack(side="left")
        tk.Frame(reader, bg=T.BORDER, height=1).pack(fill="x")

        self.body_holder = tk.Frame(reader, bg=T.PAPER)
        self.body_holder.pack(fill="both", expand=True)

        # The document viewer (a styled Text widget).
        self.doc_wrap = tk.Frame(self.body_holder, bg=T.PAPER)
        self.viewer = tk.Text(
            self.doc_wrap, font=T.font(11), bg=T.PAPER, fg=T.INK_SOFT,
            relief="flat", wrap="word", padx=34, pady=26,
            insertbackground=T.INK, bd=0, highlightthickness=0, spacing1=1,
            spacing3=4, height=1)
        self.viewer_sb = tk.Scrollbar(self.doc_wrap, orient="vertical",
                                      command=self.viewer.yview)
        self.viewer.configure(yscrollcommand=self.viewer_sb.set)
        self.viewer_sb.pack(side="right", fill="y")
        self.viewer.pack(side="left", fill="both", expand=True)
        self.viewer.bind("<Enter>", lambda e: self.viewer.bind_all(
            "<MouseWheel>", self._viewer_wheel))
        self.viewer.bind("<Leave>", lambda e: self.viewer.unbind_all("<MouseWheel>"))
        self.body_holder.bind("<Configure>", self._center_doc)
        self._style_text_tags()

    def _center_doc(self, e=None):
        """Keep the document column at a readable width, centered."""
        try:
            w = self.body_holder.winfo_width()
            pad = max(34, int((w - 660) / 2))
            self.viewer.configure(padx=pad)
        except tk.TclError:
            pass

    def _viewer_wheel(self, e):
        self.viewer.yview_scroll(int(-e.delta / 120), "units")

    def _style_text_tags(self):
        v = self.viewer
        v.tag_configure("h1", font=T.head(20), foreground=T.INK,
                        spacing1=6, spacing3=4)
        v.tag_configure("meta", font=T.med(10), foreground=T.MUTED, spacing3=16)
        v.tag_configure("meta_proj", font=T.semi(10), foreground=T.AMBER)
        v.tag_configure("secsq", font=T.bold(8), foreground=T.YELLOW,
                        spacing1=16, spacing3=7)
        v.tag_configure("seclabel", font=T.bold(8), foreground=T.MUTED,
                        spacing1=16, spacing3=7)
        v.tag_configure("body", font=T.font(11), foreground=T.INK_SOFT,
                        spacing3=7)
        v.tag_configure("bullet", font=T.font(11), foreground=T.INK_SOFT,
                        lmargin1=2, lmargin2=20, spacing3=5)
        v.tag_configure("bdot", font=T.font(11), foreground=T.AMBER)
        v.tag_configure("task", font=T.font(11), foreground=T.INK_SOFT,
                        lmargin1=2, lmargin2=26, spacing3=6)
        v.tag_configure("cbox", font=("Segoe UI Symbol", 11),
                        foreground=T.BORDER_DEEP)
        v.tag_configure("italicm", font=T.font(11), foreground=T.MUTED,
                        spacing3=7)
        v.tag_configure("tline", font=T.font(11), foreground=T.INK_SOFT,
                        tabs=("52",), lmargin2=52, spacing3=7)
        v.tag_configure("ts", font=T.med(9), foreground=T.SUBTLE)
        v.tag_configure("pill", font=T.semi(10), foreground=T.AMBER,
                        spacing1=4, spacing3=12)
        v.tag_configure("caret", font=T.semi(11), foreground=T.AMBER)
        v.tag_configure("mutedline", font=T.font(10), foreground=T.MUTED)

    # ---- rail status sub-line ----------------------------------------
    def _sub_set(self, text, color=T.INK_SOFT, dot=None, pulse=False):
        self._sub_state = (text, color, dot, pulse)
        self._sub_lbl.configure(text=text, fg=color)
        self._sub_dotc.pack_forget()
        self._sub_lbl.pack_forget()
        if dot:
            self._sub_dotc.pack(side="left", padx=(0, 5))
            self._draw_sub_dot(dot, True)
        self._sub_lbl.pack(side="left")

    def _draw_sub_dot(self, color, visible):
        self._sub_dotc.delete("all")
        c = color if visible else T.mix(color, T.YELLOW, 0.7)
        self._sub_dotc.create_oval(1, 1, 9, 9, fill=c, outline=c)

    def _sub_clear(self):
        self._sub_state = None
        self._sub_lbl.configure(text="")
        self._sub_dotc.pack_forget()

    def _toast(self, text, color=T.MUTED, dot=None):
        """A transient status under the record button (idle only)."""
        self._toast_token += 1
        token = self._toast_token
        self._sub_set(text, color, dot)

        def clear():
            if self._toast_token == token and self.state == "idle":
                self._sub_clear()
        self.root.after(3500, clear)

    # ---- project picker / nav -----------------------------------------
    def _project_label(self):
        name = self.project_var.get()
        return "No project" if (not name or name == NO_PROJECT) else name

    def _open_project_menu(self):
        pop = T.Popover(self.root, min_width=RAIL_INNER)
        cur = self.project_var.get()
        pop.item("No project", lambda: self._pick_project(NO_PROJECT),
                 selected=(cur == NO_PROJECT or not cur))
        for p in config.PROJECTS:
            n = p.get("name")
            if not n:
                continue
            if n == cur:
                pop.item(n, lambda v=n: self._pick_project(v), selected=True)
            else:
                pop.item(n, lambda v=n: self._pick_project(v),
                         swatch=T.color_for_project(p))
        pop.separator()
        pop.item("＋  Manage projects…",
                 lambda: self.open_settings(initial_tab="Projects"))
        x = self.project_pill.winfo_rootx()
        y = self.project_pill.winfo_rooty() + self.project_pill.winfo_height() + 4
        pop.open(x, y)

    def _pick_project(self, name):
        self.project_var.set(name)
        self.project_pill.set_value(self._project_label(), name != NO_PROJECT)
        config.update_settings(
            selected_project="" if name == NO_PROJECT else name)

    def _restore_selected_project(self):
        names = [p["name"] for p in config.PROJECTS if p.get("name")]
        if config.SELECTED_PROJECT in names:
            self.project_var.set(config.SELECTED_PROJECT)
            self.project_pill.set_value(self._project_label(), True)

    def _toggle_projects(self):
        self._projects_open = not self._projects_open
        self.nav_projects.set_chevron("down" if self._projects_open else "right")
        if self._projects_open:
            self._proj_holder.pack(fill="x", padx=16, after=self.nav_projects)
            self._rebuild_proj_nav()
        else:
            self._proj_holder.pack_forget()

    def _rebuild_proj_nav(self):
        for w in self._proj_holder.winfo_children():
            w.destroy()
        self._proj_items = {}
        for p in config.PROJECTS:
            n = p.get("name")
            if not n:
                continue
            item = NavItem(self._proj_holder, None, n,
                           lambda v=n: self._set_nav(v), indent=22,
                           swatch=T.color_for_project(p))
            item.pack(pady=1)
            self._proj_items[n] = item
        self._update_nav_active()

    def _set_nav(self, project):
        self._nav_filter = project
        self._update_nav_active()
        self.list_title.configure(text=project or "All conversations")
        self.refresh_list()

    def _update_nav_active(self):
        self.nav_all.set_active(self._nav_filter is None)
        for n, item in self._proj_items.items():
            item.set_active(self._nav_filter == n)

    def _refresh_projects(self):
        names = [NO_PROJECT] + [p["name"] for p in config.PROJECTS if p.get("name")]
        if self.project_var.get() not in names:
            self.project_var.set(NO_PROJECT)
        self.project_pill.set_value(self._project_label(),
                                    self.project_var.get() != NO_PROJECT)
        if self._nav_filter and self._nav_filter not in names:
            self._set_nav(None)
        if self._projects_open:
            self._rebuild_proj_nav()

    def _selected_project(self):
        name = self.project_var.get()
        if not name or name == NO_PROJECT:
            return None
        return config.find_project(name) or {"name": name, "path": ""}

    # ---- search / sort -------------------------------------------------
    def _on_search(self, text):
        self._search = text.strip().lower()
        self.refresh_list()

    def _open_sort_menu(self, e):
        pop = T.Popover(self.root, min_width=150)
        pop.item("Newest first", lambda: self._set_sort(True),
                 selected=self._sort_newest)
        pop.item("Oldest first", lambda: self._set_sort(False),
                 selected=not self._sort_newest)
        pop.open(self.sort_lbl.winfo_rootx() - 60,
                 self.sort_lbl.winfo_rooty() + 22)

    def _set_sort(self, newest):
        self._sort_newest = newest
        self.sort_lbl.configure(text="Newest ▾" if newest else "Oldest ▾")
        self.refresh_list()

    # ------------------------------------------------------------- state
    def _set_state(self, state):
        self.state = state
        if state == "idle":
            self.btn.set_text("Start recording")
            self.btn.set_colors(T.INK, "#000000", fg="white", icon="dot",
                                icon_color=T.RECORD, lip="#0A0A08")
            self.btn.set_enabled(True)
            self.btn.configure(cursor="hand2")
            self._sub_clear()
        elif state == "starting":
            self.btn.set_text("Start recording")
            self.btn.set_colors(T.INK, T.INK, fg="white", icon="dot",
                                icon_color=T.mix(T.RECORD, T.INK, 0.4),
                                lip="#0A0A08")
            self.btn.configure(cursor="arrow")
            self._sub_set("Starting…", T.INK_SOFT, dot=T.SUBTLE)
        elif state == "recording":
            self.btn.set_text("Stop recording")
            self.btn.set_colors(T.RECORD, T.RECORD_HOVER, fg="white",
                                icon="stop", icon_color="white",
                                lip="#B23438")
            self.btn.set_enabled(True)
            self.btn.configure(cursor="hand2")
            self._show_recording_view()
            self._tick_timer()
        elif state == "processing":
            self.btn.set_text("Start recording")
            self.btn.set_colors(T.INK_WASH, T.INK_WASH,
                                fg=T.mix("#FFFFFF", T.INK_WASH, 0.25),
                                icon="dot",
                                icon_color=T.mix(T.RECORD, T.INK_WASH, 0.55),
                                lip=None)
            self.btn.configure(cursor="arrow")
            self._sub_set("Transcribing…", T.AMBER, dot=T.AMBER)
            self._steps = []
            self._live_count = 0
            self._frac = None
            self._show_processing_view()
        # Cancel control: visible only while recording.
        if hasattr(self, "cancel_btn"):
            if state == "recording":
                self.cancel_btn.pack(padx=16, pady=(0, 6),
                                     before=self.project_pill)
            else:
                self.cancel_btn.pack_forget()
        self.refresh_list()
        if hasattr(self, "indicator"):
            self._update_indicator()

    def _tick_timer(self):
        if self.state != "recording":
            return
        elapsed = int(time.time() - self._rec_started) if self._rec_started else 0
        m, s = divmod(elapsed, 60)
        t = f"{m:02d}:{s:02d}"
        self._pulse_on = not self._pulse_on
        self._sub_set(f"Recording · {t}", T.INK_SOFT, dot=T.RECORD, pulse=True)
        self._draw_sub_dot(T.RECORD, self._pulse_on)
        if self._rec_card is not None:
            try:
                self._rec_card.set_time(t, self._pulse_on)
            except tk.TclError:
                pass
        if getattr(self, "_hero_timer", None) is not None:
            try:
                self._hero_timer.configure(text=t)
            except tk.TclError:
                pass
        self.root.after(500, self._tick_timer)

    # ------------------------------------------------- reader state frames
    def _clear_reader(self):
        self.doc_wrap.pack_forget()
        if self._state_frame is not None:
            self._state_frame.destroy()
            self._state_frame = None
        self._hero_timer = None

    def _state_area(self):
        self._clear_reader()
        f = tk.Frame(self.body_holder, bg=T.PAPER)
        f.pack(fill="both", expand=True)
        self._state_frame = f
        return f

    def _show_doc(self):
        if self._state_frame is not None:
            self._state_frame.destroy()
            self._state_frame = None
        self._hero_timer = None
        if not self.doc_wrap.winfo_ismapped():
            self.doc_wrap.pack(fill="both", expand=True)

    def _update_topbar(self, tabs=None, active=None, icons=False):
        if tabs:
            self.tabs.set_tabs(tabs, active)
            if not self.tabs.winfo_ismapped():
                self.tabs.pack(side="left", padx=18, pady=9)
        else:
            self.tabs.pack_forget()
        if icons:
            if not self._icons.winfo_ismapped():
                self._icons.pack(side="right", padx=18, pady=9)
        else:
            self._icons.pack_forget()

    # ---- welcome / empty ----------------------------------------------
    def _show_placeholder(self):
        self._update_topbar()
        area = self._state_area()
        inner = tk.Frame(area, bg=T.PAPER)
        inner.place(relx=0.5, rely=0.42, anchor="center")
        first_run = not self._items
        try:
            self._mascot_img = tk.PhotoImage(file=os.path.join(_ASSETS, "logo_64.png"))
            tk.Label(inner, image=self._mascot_img, bg=T.PAPER).pack(pady=(0, 10))
        except Exception:
            pass
        tk.Label(inner, text="Ready when you are", bg=T.PAPER, fg=T.INK,
                 font=T.head(16)).pack()
        helper = tk.Frame(inner, bg=T.PAPER)
        helper.pack(pady=(6, 0))
        tk.Label(helper, text="Press ", bg=T.PAPER, fg=T.MUTED,
                 font=T.font(10)).pack(side="left")
        tk.Label(helper, text="Start recording", bg=T.PAPER, fg=T.INK,
                 font=T.semi(10)).pack(side="left")
        tail = (" in the sidebar to capture your first conversation."
                if first_run else
                " to capture a conversation, or pick one from the list.")
        tk.Label(helper, text=tail, bg=T.PAPER, fg=T.MUTED,
                 font=T.font(10)).pack(side="left")
        if first_run:
            steps = tk.Frame(inner, bg=T.PAPER)
            steps.pack(pady=(26, 0))
            data = [("1", "Record", "One button captures you +\neveryone on the call"),
                    ("2", "Transcribe", "Turned into text on\nyour machine"),
                    ("3", "AI notes", "A clean summary, decisions\n& action items")]
            for n, title, desc in data:
                card = tk.Frame(steps, bg=T.SURFACE, highlightbackground=T.BORDER,
                                highlightthickness=1)
                card.pack(side="left", padx=6, ipadx=4, ipady=2)
                pad = tk.Frame(card, bg=T.SURFACE)
                pad.pack(padx=12, pady=10)
                chip = tk.Canvas(pad, width=22, height=22, bg=T.SURFACE,
                                 highlightthickness=0, bd=0)
                chip.pack(anchor="w")
                chip.create_oval(1, 1, 21, 21, fill=T.YELLOW, outline=T.YELLOW_DEEP)
                chip.create_text(11, 11, text=n, font=T.bold(9), fill=T.INK)
                tk.Label(pad, text=title, bg=T.SURFACE, fg=T.INK,
                         font=T.semi(10)).pack(anchor="w", pady=(6, 1))
                tk.Label(pad, text=desc, bg=T.SURFACE, fg=T.MUTED,
                         font=T.font(8), justify="left").pack(anchor="w")

    # ---- recording view -------------------------------------------------
    def _show_recording_view(self):
        self._update_topbar()
        area = self._state_area()
        inner = tk.Frame(area, bg=T.PAPER)
        inner.place(relx=0.5, rely=0.44, anchor="center")

        pill = tk.Canvas(inner, width=86, height=30, bg=T.PAPER,
                         highlightthickness=0, bd=0)
        pill.pack()
        T.round_rect(pill, 1, 1, 85, 29, 14, fill="#FCE9EA",
                     outline=T.mix(T.RECORD, "#FFFFFF", 0.6), width=1)
        self._rec_pill_dot = pill.create_oval(16, 11, 24, 19, fill=T.RECORD,
                                              outline=T.RECORD)
        pill.create_text(52, 15, text="REC", fill=T.RECORD, font=T.bold(9))
        self._rec_pill = pill

        self._hero_timer = tk.Label(inner, text="00:00", bg=T.PAPER, fg=T.INK,
                                    font=T.head(44))
        self._hero_timer.pack(pady=(10, 6))

        self._wave = tk.Canvas(inner, width=336, height=44, bg=T.PAPER,
                               highlightthickness=0, bd=0)
        self._wave.pack(pady=(2, 14))
        import random
        self._wave_h = [random.randint(6, 38) for _ in range(42)]

        tk.Label(inner, text="Listening to your microphone and this PC's audio",
                 bg=T.PAPER, fg=T.MUTED, font=T.font(10)).pack()
        if getattr(self.session, "bg_active", False):
            tk.Label(inner, text="Transcribing as you go, so finishing is quick",
                     bg=T.PAPER, fg=T.SUBTLE, font=T.font(9)).pack(pady=(2, 0))
        chips = tk.Frame(inner, bg=T.PAPER)
        chips.pack(pady=(10, 0))
        for label in ("Microphone", "System audio"):
            f = tkfont.Font(family=T.UI_SEMI, size=9)
            w = f.measure(label) + 38
            c = tk.Canvas(chips, width=w, height=26, bg=T.PAPER,
                          highlightthickness=0, bd=0)
            c.pack(side="left", padx=5)
            T.round_rect(c, 1, 1, w - 1, 25, 12, fill=T.WHITE, outline=T.BORDER,
                         width=1.2)
            c.create_oval(12, 10, 18, 16, fill=T.GREEN, outline=T.GREEN)
            c.create_text(26, 13, text=label, anchor="w", fill=T.INK_SOFT,
                          font=T.semi(9))
        self._animate_wave()

    def _animate_wave(self):
        if self.state != "recording" or not getattr(self, "_wave", None):
            return
        import random
        try:
            c = self._wave
            c.delete("all")
            for i, h in enumerate(self._wave_h):
                target = random.randint(5, 40)
                h = h + (target - h) * 0.25
                self._wave_h[i] = h
                x = 4 + i * 8
                cy = 22
                col = T.AMBER if i % 7 == 3 else T.INK
                if h < 9:
                    col = T.BORDER_DEEP
                c.create_line(x, cy - h / 2, x, cy + h / 2, fill=col, width=3,
                              capstyle="round")
            # Pulse the REC dot in time with the timer pulse.
            dot = T.RECORD if self._pulse_on else T.mix(T.RECORD, "#FCE9EA", 0.5)
            self._rec_pill.itemconfigure(self._rec_pill_dot, fill=dot,
                                         outline=dot)
            self.root.after(110, self._animate_wave)
        except tk.TclError:
            pass

    # ---- processing view ------------------------------------------------
    _STEP_MAP = [
        (re.compile(r"^Saving the recording"), "Saving the recording",
         "Saved the recording"),
        (re.compile(r"^Mixing"), "Mixing microphone + system audio",
         "Mixed microphone + system audio"),
        (re.compile(r"^Loading the Whisper (\w+)"), "Loading the {0} model",
         "Loaded the {0} model"),
        (re.compile(r"^Transcribing"), "Transcribing the audio",
         "Transcribed the audio"),
    ]

    def _step_labels(self, raw):
        for rx, active, done in self._STEP_MAP:
            m = rx.match(raw)
            if m:
                g = m.groups()
                return active.format(*g), done.format(*g)
        return raw, raw

    def _show_processing_view(self):
        self._update_topbar()
        area = self._state_area()
        doc = tk.Frame(area, bg=T.PAPER)
        doc.pack(fill="both", expand=True, padx=44, pady=(30, 16))
        tk.Label(doc, text="Processing your conversation", bg=T.PAPER,
                 fg=T.INK, font=T.head(18), anchor="w").pack(fill="x",
                                                             pady=(0, 14))
        self._steps_holder = tk.Frame(doc, bg=T.PAPER)
        self._steps_holder.pack(fill="x")
        self._step_rows = []

        self._bar = tk.Canvas(doc, width=520, height=6, bg=T.PAPER,
                              highlightthickness=0, bd=0)
        self._bar.pack(anchor="w", pady=(12, 4))

        lab = tk.Frame(doc, bg=T.PAPER)
        lab.pack(fill="x", pady=(14, 4))
        tk.Label(lab, text="■", bg=T.PAPER, fg=T.YELLOW, font=T.bold(8)).pack(
            side="left")
        tk.Label(lab, text="  TRANSCRIPT SO FAR", bg=T.PAPER, fg=T.MUTED,
                 font=T.bold(8)).pack(side="left")
        self._live = tk.Text(doc, font=T.font(11), bg=T.PAPER, fg=T.INK_SOFT,
                             relief="flat", wrap="word", bd=0,
                             highlightthickness=0, spacing3=7)
        self._live.tag_configure("tline", font=T.font(11), foreground=T.MUTED,
                                 tabs=("52",), lmargin2=52, spacing3=7)
        self._live.tag_configure("tnew", font=T.semi(11), foreground=T.INK,
                                 tabs=("52",), lmargin2=52, spacing3=7)
        self._live.tag_configure("ts", font=T.med(9), foreground=T.SUBTLE)
        self._live.tag_configure("caret", font=T.semi(11), foreground=T.AMBER)
        self._live.tag_configure("mutedline", font=T.font(10),
                                 foreground=T.MUTED)
        self._live.insert("end", "Listening for speech…", "mutedline")
        self._live.configure(state="disabled")
        self._live.pack(fill="both", expand=True)
        self._spin_angle = 0
        self._caret_on = True
        self._spin_tick()
        self._draw_bar()

    def _draw_bar(self):
        if not getattr(self, "_bar", None):
            return
        try:
            b = self._bar
            b.delete("all")
            T.round_rect(b, 0, 0, 520, 6, 3, fill=T.CARD, outline=T.CARD)
            frac = self._frac or 0.0
            if frac > 0.01:
                T.round_rect(b, 0, 0, max(8, 520 * frac), 6, 3, fill=T.AMBER,
                             outline=T.AMBER)
        except tk.TclError:
            pass

    def _add_step_row(self, raw):
        active, done = self._step_labels(raw)
        row = tk.Frame(self._steps_holder, bg=T.PAPER)
        row.pack(fill="x", pady=3)
        icon = tk.Canvas(row, width=22, height=22, bg=T.PAPER,
                         highlightthickness=0, bd=0)
        icon.pack(side="left")
        lbl = tk.Label(row, text=active, bg=T.PAPER, fg=T.INK, font=T.semi(10),
                       anchor="w")
        lbl.pack(side="left", padx=(8, 0))
        pct = tk.Label(row, text="", bg=T.PAPER, fg=T.AMBER, font=T.semi(10))
        pct.pack(side="right")
        self._step_rows.append({"icon": icon, "lbl": lbl, "pct": pct,
                                "active": active, "done": done,
                                "state": "active"})
        self._paint_step_icons()

    def _finish_active_steps(self):
        for r in self._step_rows:
            if r["state"] == "active":
                r["state"] = "done"
                r["lbl"].configure(text=r["done"], fg=T.MUTED, font=T.med(10))
                r["pct"].configure(text="")
        self._paint_step_icons()

    def _paint_step_icons(self):
        for r in self._step_rows:
            c = r["icon"]
            try:
                c.delete("all")
                if r["state"] == "done":
                    c.create_oval(1, 1, 21, 21, fill=T.GREEN_SOFT,
                                  outline=T.GREEN_SOFT)
                    T.draw_icon(c, "check", 11, 11, 10, T.GREEN, 2.0)
                else:
                    c.create_arc(3, 3, 19, 19, start=self._spin_angle,
                                 extent=260, style="arc", outline=T.AMBER,
                                 width=2)
            except tk.TclError:
                pass

    def _spin_tick(self):
        if self.state != "processing":
            return
        try:
            self._spin_angle = (self._spin_angle - 24) % 360
            for r in self._step_rows:
                if r["state"] == "active":
                    c = r["icon"]
                    c.delete("all")
                    c.create_arc(3, 3, 19, 19, start=self._spin_angle,
                                 extent=260, style="arc", outline=T.AMBER,
                                 width=2)
            # Blink the live-transcript caret.
            self._caret_on = not self._caret_on
            self._live.tag_configure(
                "caret", foreground=T.AMBER if self._caret_on else T.PAPER)
            self.root.after(120, self._spin_tick)
        except tk.TclError:
            pass

    def progress(self, kind, value):
        self.root.after(0, lambda: self._apply_progress(kind, value))

    def _apply_progress(self, kind, value):
        if self.state != "processing":
            return
        if kind == "step":
            self._finish_active_steps()
            self._add_step_row(value)
            self._frac = 0.0 if value.startswith("Transcribing") else None
            self._draw_bar()
            active = self._step_labels(value)[0]
            self._sub_set(active + "…" if not active.endswith("…") else active,
                          T.AMBER, dot=T.AMBER)
        elif kind == "seg":
            self._frac, line = value[0], value[1]
            pct = f"{int(self._frac * 100)}%"
            for r in self._step_rows:
                if r["state"] == "active":
                    r["pct"].configure(text=pct)
            self._sub_set(f"Transcribing… {pct}", T.AMBER, dot=T.AMBER)
            self._draw_bar()
            self._append_live_line(line)
        elif kind == "bar":
            # Move the progress bar without adding a transcript line (used to
            # jump straight to the portion already transcribed in the background).
            self._frac = max(0.0, min(float(value), 1.0))
            pct = f"{int(self._frac * 100)}%"
            for r in self._step_rows:
                if r["state"] == "active":
                    r["pct"].configure(text=pct)
            self._sub_set(f"Transcribing… {pct}", T.AMBER, dot=T.AMBER)
            self._draw_bar()

    _TS_RE = re.compile(r"^\[(\d+:\d{2}(?::\d{2})?)\]\s*(.*)$")

    def _append_live_line(self, line):
        v = self._live
        try:
            v.configure(state="normal")
            if self._live_count == 0:
                v.delete("1.0", "end")
            # Remove the previous caret.
            idx = v.search("▌", "1.0", "end")
            if idx:
                v.delete(idx, f"{idx}+1c")
            self._live_count += 1
            m = self._TS_RE.match(line.strip())
            if m:
                ts, text = m.groups()
                v.insert("end", ts, "ts")
                v.insert("end", "\t" + text, "tnew")
            else:
                v.insert("end", line, "tnew")
            v.insert("end", " ▌", "caret")
            v.insert("end", "\n")
            # Demote all but the last two lines.
            total = int(v.index("end-1c").split(".")[0])
            for ln in range(1, max(1, total - 2)):
                v.tag_remove("tnew", f"{ln}.0", f"{ln}.end")
                v.tag_add("tline", f"{ln}.0", f"{ln}.end")
            v.see("end")
            v.configure(state="disabled")
        except tk.TclError:
            pass

    # ------------------------------------------------- live AI-notes view
    _SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def _gen_spin_tick(self):
        if not self._generating:
            return
        try:
            self._gen_spin = (self._gen_spin + 1) % len(self._SPINNER)
            self._render_notes_generating()
            self.root.after(150, self._gen_spin_tick)
        except tk.TclError:
            pass

    def generate_ai_notes(self):
        if self._generating or self.state != "idle":
            return
        base = self._selected_base()
        if not base:
            return
        # Too short to summarise? Resolve it instantly - no spinner, no model.
        try:
            with open(base + "_transcript.txt", encoding="utf-8") as f:
                tx = f.read()
        except OSError:
            tx = ""
        if engine.is_too_short(tx):
            engine.generate_notes(base)  # instant; writes the short note
            self.refresh_list()
            self._select_base(base)
            self._toast("Too short for notes", T.MUTED, dot=T.SUBTLE)
            return

        self._generating = True
        self._gen_base = base
        self._notes_buf = []
        self._gen_spin = 0
        self._gen_phase = "Loading %s" % config.SUMMARY_MODEL
        self._update_topbar()
        self._sub_set("Writing notes…", T.AMBER, dot=T.AMBER)
        self._show_doc()
        self._render_notes_generating()
        self._gen_spin_tick()
        threading.Thread(target=self._do_generate, args=(base,), daemon=True).start()

    def regenerate_ai_notes(self):
        """Re-run notes generation for the selected conversation, overwriting the
        existing notes using the latest prompt (config.SUMMARY_PROMPT)."""
        if self._generating or self.state != "idle":
            return
        base = self._selected_base()
        if not base or not os.path.exists(base + "_notes.md"):
            return
        if not messagebox.askyesno(
                config.APP_NAME,
                "Regenerate these notes from the transcript using your current "
                "prompt?\n\nThis replaces the existing notes."):
            return
        # generate_ai_notes streams with config.SUMMARY_PROMPT and engine
        # rewrites _notes.md, so it naturally overrides the old notes.
        self.generate_ai_notes()

    def _do_generate(self, base):
        try:
            engine.generate_notes(base, on_token=self._on_notes_token,
                                  model=config.SUMMARY_MODEL,
                                  prompt=config.SUMMARY_PROMPT)
            self.root.after(0, lambda: self._on_notes_done(base))
        except summarize.SummarizeError as e:
            msg = str(e)
            self.root.after(0, lambda: self._on_notes_error(msg))
        except Exception as e:
            log.exception("Notes generation failed")
            msg = str(e)
            self.root.after(0, lambda: self._on_notes_error(msg))

    def _on_notes_token(self, chunk):
        self.root.after(0, lambda: self._append_notes_token(chunk))

    def _append_notes_token(self, chunk):
        if not self._generating:
            return
        if not self._notes_buf:  # first token has arrived - model is loaded
            self._gen_phase = "Writing notes"
        self._notes_buf.append(chunk)
        self._render_notes_generating()

    def _render_notes_generating(self):
        dots = "." * (1 + (self._gen_spin // 3) % 3)
        v = self.viewer
        v.configure(state="normal")
        v.delete("1.0", "end")
        self._insert_doc_header(v, self._gen_base)
        v.insert("end", f"✦  {self._gen_phase}{dots}\n", "pill")
        text = "".join(self._notes_buf).strip()
        if text:
            self._insert_notes_md(v, text)
            v.insert("end", "▌", "caret")
        v.see("end")
        v.configure(state="disabled")

    def _on_notes_done(self, base):
        self._generating = False
        self._toast("Notes saved", T.GREEN, dot=T.GREEN)
        self.refresh_list()
        self._select_base(base)

    def _on_notes_error(self, msg):
        self._generating = False
        self._sub_clear()
        self._select_base(getattr(self, "_gen_base", None))
        messagebox.showinfo(config.APP_NAME, msg)

    # ----------------------------------------------------- generate CTA
    def _show_generate_cta(self, item):
        area = self._state_area()
        inner = tk.Frame(area, bg=T.PAPER)
        inner.place(relx=0.5, rely=0.42, anchor="center")
        tile = tk.Canvas(inner, width=56, height=56, bg=T.PAPER,
                         highlightthickness=0, bd=0)
        tile.pack()
        T.round_rect(tile, 2, 2, 54, 54, 16, fill=T.YELLOW,
                     outline=T.YELLOW_DEEP, width=1.2)
        T.draw_icon(tile, "sparkle", 28, 28, 22, T.INK)
        tk.Label(inner, text="Turn this into clean notes", bg=T.PAPER,
                 fg=T.INK, font=T.head(15)).pack(pady=(14, 4))
        tk.Label(inner, text="You have a transcript. Generate a summary, "
                 "decisions and action\nitems — written locally on your machine.",
                 bg=T.PAPER, fg=T.MUTED, font=T.font(10),
                 justify="center").pack()
        T.RoundedButton(inner, "Generate AI meeting notes",
                        command=self.generate_ai_notes, fill=T.YELLOW,
                        fill_hover=T.YELLOW_HOVER, fg=T.INK, bg=T.PAPER,
                        font_=T.semi(11), padx=22, pady=11, radius=12,
                        icon="sparkle", icon_color=T.INK,
                        lip=T.YELLOW_DEEP).pack(pady=(16, 10))
        lock = tk.Frame(inner, bg=T.PAPER)
        lock.pack()
        lc = tk.Canvas(lock, width=14, height=14, bg=T.PAPER,
                       highlightthickness=0, bd=0)
        lc.pack(side="left", padx=(0, 4))
        T.draw_icon(lc, "lock", 7, 8, 11, T.SUBTLE)
        model = (config.SUMMARY_MODEL or "a local model").split(":")[0]
        tk.Label(lock, text=f"Runs locally with {model} · nothing leaves "
                 "your PC", bg=T.PAPER, fg=T.SUBTLE, font=T.font(9)).pack(
            side="left")

    # ----------------------------------------------------- doc rendering
    _EMPH_RE = re.compile(r"(?<!\w)[_*]{1,2}(?=\S)(.+?)(?<=\S)[_*]{1,2}(?!\w)")

    def _md_clean(self, s):
        """Drop markdown emphasis markers (**bold**, _italic_, *italic*)."""
        return self._EMPH_RE.sub(r"\1", s).replace("**", "")

    def _insert_doc_header(self, v, base):
        it = self._items_by_base.get(base)
        title = (it and it["title"]) or None
        if not title:
            stamp, tag = engine.parse_base(base)
            title = tag or "Conversation"
        v.insert("end", title + "\n", "h1")
        if it:
            v.insert("end", it["date"], "meta")
            if it["project"]:
                v.insert("end", "   •   ", "meta")
                v.insert("end", "■ ", ("meta_proj",))
                v.insert("end", it["project"], "meta_proj")
            if it["duration"]:
                v.insert("end", "   •   " + it["duration"], "meta")
            v.insert("end", "\n", "meta")

    _TASK_RE = re.compile(r"^\s*[-*]\s*\[[ xX]?\]\s*(.*)$")

    def _insert_notes_md(self, v, text):
        """Markdown -> the styled notes document. Consecutive plain lines are
        joined into one paragraph (models often hard-wrap their output)."""
        para = []

        def flush():
            if para:
                v.insert("end", " ".join(para) + "\n", "body")
                para.clear()

        for raw in text.split("\n"):
            line = raw.rstrip()
            if not line.strip():
                flush()
                continue
            task = self._TASK_RE.match(line)
            if line.startswith(("## ", "### ", "# ")):
                flush()
                label = self._md_clean(line.lstrip("#").strip()).upper()
                v.insert("end", "■  ", "secsq")
                v.insert("end", label + "\n", "seclabel")
            elif task:
                flush()
                v.insert("end", "☐  ", "cbox")
                v.insert("end", self._md_clean(task.group(1)) + "\n", "task")
            elif line.lstrip().startswith(("- ", "* ", "• ")):
                flush()
                content = self._md_clean(line.lstrip().lstrip("-*•").strip())
                if content.lower().startswith("none"):
                    v.insert("end", content + "\n", "italicm")
                else:
                    v.insert("end", "•  ", "bdot")
                    v.insert("end", content + "\n", "bullet")
            elif raw.strip().startswith("_") and raw.strip().endswith("_"):
                flush()
                v.insert("end", self._md_clean(line.strip()) + "\n", "italicm")
            else:
                para.append(self._md_clean(line.strip()))
        flush()

    def _insert_transcript(self, v, text):
        for raw in text.split("\n"):
            line = raw.strip()
            if not line:
                continue
            m = self._TS_RE.match(line)
            if m:
                ts, content = m.groups()
                v.insert("end", ts, "ts")
                v.insert("end", "\t" + content + "\n", "tline")
            else:
                v.insert("end", line + "\n", "tline")

    # ------------------------------------------------------------- actions
    def on_toggle(self):
        if self._generating:
            return
        if self.state == "idle":
            self.start_recording()
        elif self.state == "recording":
            self.stop_recording()

    def on_close(self):
        if self.state in ("recording", "starting") and self.session:
            try:
                self.session.cancel()
            except Exception:
                pass
        try:  # remember the window size/position for next launch
            config.update_settings(window_geometry=self.root.winfo_geometry())
        except Exception:
            pass
        self.root.destroy()

    def open_settings(self, initial_tab=None):
        SettingsWindow(self.root, on_saved=self._on_settings_saved,
                       initial_tab=initial_tab,
                       on_bg_download=self._on_bg_download)

    def _on_bg_download(self, active, label):
        """Settings was closed while a model was still downloading — show (or
        clear) a banner on the main window. Safe to call from any thread."""
        text = (f"Downloading {label} in the background — you can keep working…"
                if active else None)
        self._banner_async(text)
        if not active:
            # Finished: refresh anything that depended on the new model.
            try:
                self.root.after(0, self._on_settings_saved)
            except tk.TclError:
                pass

    def _on_settings_saved(self):
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
        self._refresh_projects()
        self.refresh_list()
        self._toast("Settings saved", T.GREEN, dot=T.GREEN)

    # ---- copy / reveal ---------------------------------------------------
    def _current_doc_path(self):
        base = self._current_base
        if not base:
            return None
        if self._view_mode == "notes" and os.path.exists(base + "_notes.md"):
            return base + "_notes.md"
        if os.path.exists(base + "_transcript.txt"):
            return base + "_transcript.txt"
        return None

    def _copy_doc(self):
        path = self._current_doc_path()
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._toast("Copied to clipboard", T.GREEN, dot=T.GREEN)
        except (OSError, tk.TclError):
            pass

    def _reveal_doc(self):
        path = self._current_doc_path() or (
            self._current_base + ".wav" if self._current_base else None)
        if path and os.path.exists(path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])

    # ---- recording lifecycle (start is async so the UI never freezes) ----
    def start_recording(self):
        log.info("Starting recording...")
        self.session = engine.RecordingSession(project=self._selected_project())
        self._set_state("starting")
        threading.Thread(target=self._do_start, daemon=True).start()

    def _do_start(self):
        try:
            self.session.start()
            self.root.after(0, self._on_started)
        except Exception as e:
            log.exception("Failed to start recording")
            self.root.after(0, lambda e=e: self._on_start_failed(e))

    def _on_started(self):
        self._rec_started = time.time()
        self._set_state("recording")
        log.info("Recording started.")

    def _on_start_failed(self, e):
        self.session = None
        self._set_state("idle")
        self._restore_reader()
        messagebox.showerror(config.APP_NAME, f"Could not start recording:\n\n{e}")

    def stop_recording(self):
        log.info("Stop pressed - beginning processing.")
        self._set_state("processing")
        threading.Thread(target=self._process, daemon=True).start()

    def _cancel_recording(self):
        if self.state != "recording":
            return
        if not messagebox.askyesno(
                config.APP_NAME,
                "Cancel this recording?\n\n"
                "The recording will be discarded and can't be recovered."):
            return
        log.info("Recording cancelled by user.")
        sess, self.session = self.session, None
        self._set_state("idle")
        self._restore_reader()
        self._toast("Recording cancelled", T.MUTED, dot=T.SUBTLE)
        # Tearing down the recorder + background transcriber does I/O, so do it
        # off the UI thread.
        if sess is not None:
            threading.Thread(target=sess.cancel, daemon=True).start()

    def _process(self):
        try:
            result = self.session.stop(model_size=config.WHISPER_MODEL,
                                       progress=self.progress)
            log.info("Captured %.1fs; transcript %d chars.",
                     result["duration"], len(result["transcript"]))
            self.root.after(0, lambda: self._on_done(result["base"]))
        except Exception as e:
            log.exception("Processing failed")
            msg = str(e)
            self.root.after(0, lambda: self._on_error(msg))
        finally:
            self.session = None

    def _on_done(self, base):
        self._set_state("idle")
        self._toast("Saved", T.GREEN, dot=T.GREEN)
        self.refresh_list()
        self._select_base(base)

    def _on_error(self, msg):
        self._set_state("idle")
        self._restore_reader()
        messagebox.showerror(
            config.APP_NAME,
            f"Something went wrong:\n\n{msg}\n\nDetails are in the logs folder.")

    def _restore_reader(self):
        if self._conv_selected:
            self._select_base(self._conv_selected)
        else:
            self._show_placeholder()

    # ---- crash recovery (finish recordings a previous run was cut off on) ----
    def _check_interrupted(self):
        try:
            self._recover_queue = engine.find_interrupted()
        except Exception:
            log.exception("Scan for interrupted recordings failed")
            self._recover_queue = []
        self._prompt_next_recovery()

    def _prompt_next_recovery(self):
        if self.state != "idle" or not self._recover_queue:
            return
        item = self._recover_queue[0]
        proj = (item.get("project") or {}).get("name")
        where = f"\n\nProject: {proj}" if proj else ""
        if messagebox.askyesno(
                config.APP_NAME,
                "An unfinished recording from a previous session was found — it "
                "looks like YapYapYap closed before it could be transcribed.\n\n"
                "The audio was saved safely. Finish transcribing it now?" + where):
            self._recover_queue.pop(0)
            self._start_recovery(item["base"])
            return
        # Not now: keep it for next launch, or offer to throw it away.
        if messagebox.askyesno(
                config.APP_NAME,
                "Keep this unfinished recording for later?\n\n"
                "Yes — keep it (you'll be asked again next time).\n"
                "No — delete the audio permanently."):
            self._recover_queue.pop(0)
        else:
            engine.discard_interrupted(item["base"])
            self._recover_queue.pop(0)
        self.refresh_list()
        self._prompt_next_recovery()

    def _start_recovery(self, base):
        log.info("Recovering interrupted recording: %s", base)
        self._set_state("processing")
        self._sub_set("Recovering…", T.AMBER, dot=T.AMBER)
        threading.Thread(target=self._do_recover, args=(base,), daemon=True).start()

    def _do_recover(self, base):
        try:
            result = engine.recover(base, model_size=config.WHISPER_MODEL,
                                    progress=self.progress)
            self.root.after(0, lambda: self._on_recovered(result["base"]))
        except Exception as e:
            log.exception("Recovery failed")
            msg = str(e)
            self.root.after(0, lambda: self._on_recover_error(base, msg))

    def _on_recovered(self, base):
        self._set_state("idle")
        self._toast("Recording recovered", T.GREEN, dot=T.GREEN)
        self.refresh_list()
        self._select_base(base)
        self.root.after(400, self._prompt_next_recovery)

    def _on_recover_error(self, base, msg):
        self._set_state("idle")
        self._restore_reader()
        messagebox.showerror(
            config.APP_NAME,
            f"Couldn't recover that recording:\n\n{msg}\n\n"
            "The audio is still saved; you can try again next launch.")
        self.root.after(400, self._prompt_next_recovery)

    # ----------------------------------------------------- list + viewer
    def _filtered_items(self):
        items = self._items
        if self._nav_filter:
            items = [it for it in items if it["project"] == self._nav_filter]
        if self._search:
            q = self._search
            items = [it for it in items
                     if q in (it["title"] or "").lower()
                     or q in (it["project"] or "").lower()
                     or q in it["date"].lower()]
        if not self._sort_newest:
            items = list(reversed(items))
        return items

    def refresh_list(self):
        self._items = scan_conversations()
        self._items_by_base = {it["base"]: it for it in self._items}
        for w in self.conv_scroll.body.winfo_children():
            w.destroy()
        self._conv_cards = {}
        self._rec_card = None

        if self.state in ("starting", "recording"):
            self._rec_card = RecordingCard(self.conv_scroll.body,
                                           self._project_label())
            self._rec_card.pack(fill="x", padx=6, pady=(2, 2))

        shown = self._filtered_items()
        n = len(shown)
        self.count_lbl.configure(
            text=f"{n} conversation" + ("" if n == 1 else "s"))
        if not shown and self.state == "idle":
            msg = ("Conversations you record will appear\nhere, newest first."
                   if not self._items else "Nothing matches your search.")
            head_txt = ("No conversations yet" if not self._items
                        else "No results")
            holder = tk.Frame(self.conv_scroll.body, bg=T.SURFACE)
            holder.pack(fill="x", padx=12, pady=14)
            tk.Label(holder, text=head_txt, bg=T.SURFACE, fg=T.MUTED,
                     font=T.semi(10), anchor="w").pack(fill="x")
            tk.Label(holder, text=msg, bg=T.SURFACE, fg=T.SUBTLE,
                     font=T.font(9), anchor="w", justify="left").pack(
                fill="x", pady=(4, 0))
            return
        for it in shown:
            card = ConvCard(self.conv_scroll.body, it, self._select_conv,
                            self._conv_menu)
            card.pack(fill="x", padx=6, pady=2)
            self._conv_cards[it["base"]] = card
        self._highlight_selected()

    def _highlight_selected(self):
        for base, card in self._conv_cards.items():
            card.set_selected(base == self._conv_selected)

    def _select_base(self, base):
        self._select_conv(base)

    def _selected_base(self):
        return self._conv_selected

    def _select_conv(self, base):
        if self._generating or self.state == "processing":
            return
        self._conv_selected = base
        self._current_base = base
        self._highlight_selected()
        if self.state in ("recording", "starting"):
            return  # keep the live view; selection applies after
        has_notes = os.path.exists(base + "_notes.md")
        has_tx = os.path.exists(base + "_transcript.txt")
        self._view_mode = "notes" if (has_notes or has_tx) else "transcript"
        if not has_notes and has_tx:
            self._view_mode = "notes"  # Notes tab shows the generate CTA
        self._render_conversation()

    def _render_conversation(self):
        base = self._current_base
        if not base:
            self._show_placeholder()
            return
        it = self._items_by_base.get(base)
        has_notes = os.path.exists(base + "_notes.md")
        has_tx = os.path.exists(base + "_transcript.txt")

        tabs = []
        if has_notes or has_tx:
            tabs.append(("notes", "Notes"))
        if has_tx:
            tabs.append(("transcript", "Transcript"))
        self._update_topbar(tabs or None, self._view_mode, icons=bool(tabs))

        # Offer "regenerate" only when notes already exist and we're showing them.
        self.regen_btn.pack_forget()
        if has_notes and has_tx and self._view_mode == "notes":
            self.regen_btn.pack(side="left", padx=(0, 8), before=self.copy_btn)

        if self._view_mode == "notes" and not has_notes and has_tx:
            self._show_generate_cta(it)
            return

        self._show_doc()
        v = self.viewer
        v.configure(state="normal")
        v.delete("1.0", "end")
        self._insert_doc_header(v, base)
        notes_path = base + "_notes.md"
        tx_path = base + "_transcript.txt"
        if self._view_mode == "notes" and os.path.exists(notes_path):
            with open(notes_path, encoding="utf-8") as f:
                self._insert_notes_md(v, f.read().strip())
        elif os.path.exists(tx_path):
            with open(tx_path, encoding="utf-8") as f:
                self._insert_transcript(v, f.read().strip())
        elif os.path.exists(base + ".wav"):
            v.insert("end", "Audio only — this recording has no transcript "
                     "yet.", "italicm")
        else:
            v.insert("end", "The files for this conversation could not be "
                     "found.", "italicm")
        v.configure(state="disabled")
        v.yview_moveto(0.0)

    def _set_view_mode(self, mode):
        self._view_mode = mode
        self._render_conversation()

    # ---- per-conversation "..." menu --------------------------------
    _CONV_SUFFIXES = (".wav", "_transcript.txt", "_notes.md", "_title.txt",
                      ".titlelock", ".mic.wav", ".sys.wav", ".hidden")

    def _conv_menu(self, base, event):
        if self._generating or self.state in ("processing", "starting", "recording"):
            return
        cur = engine.parse_base(base)[1]
        pop = T.Popover(self.root, min_width=210)
        pop.label("Assign to project")
        pop.item("No project", lambda: self._assign_project(base, None),
                 selected=not cur)
        for p in config.PROJECTS:
            nm = p.get("name", "")
            if not nm:
                continue
            sel = engine.project_tag(p) == cur
            pop.item(nm, lambda n=nm: self._assign_project(base, n),
                     selected=sel,
                     swatch=None if sel else T.color_for_project(p))
        pop.separator()
        pop.item("Rename", lambda: self._rename_conv(base))
        pop.item("Delete from computer", lambda: self._delete_conv(base),
                 danger=True)
        pop.open(event.x_root - 10, event.y_root + 8)

    def _assign_project(self, base, project_name):
        project = (config.find_project(project_name) or {"name": project_name,
                   "path": ""}) if project_name else None
        stamp, _ = engine.parse_base(base)
        new_base = engine.base_for(stamp, project)
        if new_base != base:
            for suf in self._CONV_SUFFIXES:
                if os.path.exists(base + suf):
                    try:
                        os.replace(base + suf, new_base + suf)
                    except OSError:
                        log.exception("Could not move %s", base + suf)
        try:
            engine.export_conversation(new_base)  # file it under the new project
        except Exception:
            log.exception("Re-export after project change failed")
        self.refresh_list()
        self._select_base(new_base)
        self._toast("Project updated", T.GREEN, dot=T.GREEN)

    def _rename_conv(self, base):
        item = self._items_by_base.get(base) if hasattr(self, "_items_by_base") else None
        current = (item and item.get("title")) or ""
        new = simpledialog.askstring(
            "Rename conversation", "Name for this conversation:",
            initialvalue=current, parent=self.root)
        if new is None:
            return  # cancelled
        new = new.strip()
        try:
            if new:
                with open(base + "_title.txt", "w", encoding="utf-8") as f:
                    f.write(new)
                # Mark the title as user-set so regenerating AI notes won't
                # overwrite it.
                open(base + ".titlelock", "w").close()
            else:
                # Cleared the name: drop the custom title and let AI notes name
                # it again next time.
                for suf in ("_title.txt", ".titlelock"):
                    try:
                        os.remove(base + suf)
                    except OSError:
                        pass
        except OSError:
            log.exception("Could not rename conversation")
            self._toast("Couldn't rename", T.RECORD, dot=T.RECORD)
            return
        self.refresh_list()
        self._select_base(base)
        self._toast("Renamed", T.GREEN, dot=T.GREEN)

    def _delete_conv(self, base):
        if not messagebox.askyesno(
                config.APP_NAME,
                "Delete this conversation from your computer?\n\n"
                "The audio, transcript and notes will be permanently removed."):
            return
        for suf in self._CONV_SUFFIXES:
            try:
                os.remove(base + suf)
            except OSError:
                pass
        self._after_remove(base)
        self._toast("Deleted")

    def _after_remove(self, base):
        if self._conv_selected == base:
            self._conv_selected = None
            self._current_base = None
            self._show_placeholder()
        self.refresh_list()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
