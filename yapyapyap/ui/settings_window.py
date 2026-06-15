"""
settings_window.py
------------------
The Settings dialog, opened from the rail. Organised into four tabs:

  * General   - save folders
  * AI Models - transcription (Whisper) + note generation (Ollama) models
  * AI Notes  - the editable prompt used to generate meeting notes
  * Projects  - add/remove named projects, each with its own save folder

Saving writes settings.json (via config.save_settings); changes take effect on
the next recording / next time notes are generated, because the worker processes
are launched fresh each time.
"""

import os
import threading

import tkinter as tk
from tkinter import filedialog, ttk

from yapyapyap import config
from yapyapyap.ui import theme as T
from yapyapyap.managers import ollama_manager as om
from yapyapyap.managers import whisper_manager as wm

_ASSETS = config.ASSETS_DIR
TABS = ("General", "AI Models", "AI Notes", "Projects")


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_saved=None, initial_tab=None):
        super().__init__(parent)
        self.on_saved = on_saved
        self.title("Settings")
        self.configure(bg=T.SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Read the live, resolved values (folders show their real on-disk path).
        self.v_model = tk.StringVar(value=config.WHISPER_MODEL)
        self.v_summary = tk.StringVar(value=config.SUMMARY_MODEL)
        self.v_rec = tk.StringVar(value=config.RECORDINGS_DIR)
        self.v_tx = tk.StringVar(value=config.TRANSCRIPTS_DIR)
        self._prompt_default = config.DEFAULT_SUMMARY_PROMPT
        self._projects = [dict(p) for p in config.PROJECTS]
        self._proj_rows = []

        self._build()
        self._show_tab(initial_tab if initial_tab in TABS else "General")
        self.geometry("720x600")
        self.update_idletasks()
        self._center_on(parent)

    # ------------------------------------------------------------------ ui
    def _build(self):
        # Yellow title band.
        band = tk.Frame(self, bg=T.YELLOW)
        band.pack(fill="x")
        binner = tk.Frame(band, bg=T.YELLOW)
        binner.pack(fill="x", padx=18, pady=10)
        try:
            self._logo = tk.PhotoImage(file=os.path.join(_ASSETS, "logo_32.png"))
            tk.Label(binner, image=self._logo, bg=T.YELLOW).pack(side="left",
                                                                 padx=(0, 8))
        except Exception:
            self._logo = None
        tk.Label(binner, text="Settings", bg=T.YELLOW, fg=T.INK,
                 font=T.head(13)).pack(side="left")
        tk.Frame(self, bg=T.YELLOW_DEEP, height=1).pack(fill="x")

        # Tab bar (underline style).
        self._tabbar = tk.Frame(self, bg=T.SURFACE)
        self._tabbar.pack(fill="x", padx=22)
        self._tab_btns = {}
        self._tabs = {}
        tk.Frame(self, bg=T.BORDER, height=1).pack(fill="x")

        # Footer pinned to the bottom (packed before the body).
        footer = tk.Frame(self, bg=T.SURFACE)
        footer.pack(side="bottom", fill="x")
        tk.Frame(footer, bg=T.BORDER, height=1).pack(fill="x")
        btns = tk.Frame(footer, bg=T.SURFACE)
        btns.pack(fill="x", padx=22, pady=12)
        T.AccentButton(btns, "Save", self._save, bg=T.SURFACE).pack(side="right")
        T.GhostButton(btns, "Cancel", self.destroy, bg=T.SURFACE).pack(
            side="right", padx=(0, 10))

        self._body = tk.Frame(self, bg=T.SURFACE)
        self._body.pack(side="top", fill="both", expand=True, padx=22, pady=18)

        for name in TABS:
            frame = tk.Frame(self._body, bg=T.SURFACE)
            self._tabs[name] = frame
            holder = tk.Frame(self._tabbar, bg=T.SURFACE)
            holder.pack(side="left", padx=(0, 22))
            lbl = tk.Label(holder, text=name, bg=T.SURFACE, fg=T.MUTED,
                           font=T.semi(10), pady=9, cursor="hand2")
            lbl.pack()
            line = tk.Frame(holder, bg=T.SURFACE, height=3)
            line.pack(fill="x")
            lbl.bind("<Button-1>", lambda e, n=name: self._show_tab(n))
            self._tab_btns[name] = (lbl, line)

        self._build_general(self._tabs["General"])
        self._build_models(self._tabs["AI Models"])
        self._build_notes(self._tabs["AI Notes"])
        self._build_projects(self._tabs["Projects"])

    def _show_tab(self, name):
        for n, f in self._tabs.items():
            f.pack_forget()
            lbl, line = self._tab_btns[n]
            lbl.configure(fg=T.MUTED, font=T.semi(10))
            line.configure(bg=T.SURFACE)
        self._tabs[name].pack(fill="both", expand=True)
        lbl, line = self._tab_btns[name]
        lbl.configure(fg=T.INK, font=T.bold(10))
        line.configure(bg=T.YELLOW_DEEP)

    # ---- General tab -------------------------------------------------
    def _build_general(self, p):
        intro = tk.Frame(p, bg=T.SURFACE)
        intro.pack(anchor="w", pady=(2, 18))
        tk.Label(intro, text="Transcription and note-writing models — including "
                 "downloads — live on the ", bg=T.SURFACE, fg=T.MUTED,
                 font=T.font(10)).pack(side="left")
        tk.Label(intro, text="AI Models", bg=T.SURFACE, fg=T.INK,
                 font=T.semi(10)).pack(side="left")
        tk.Label(intro, text=" tab.", bg=T.SURFACE, fg=T.MUTED,
                 font=T.font(10)).pack(side="left")

        self._section(p, "Recordings folder",
                      "Master history — every conversation is saved here.")
        self._path_row(p, self.v_rec)

        self._section(p, "Default transcripts folder",
                      "Where the tidy copy goes when no project is selected.")
        self._path_row(p, self.v_tx)

    # ---- AI Models tab ----------------------------------------------
    def _build_models(self, p):
        self._scroll = T.ScrollFrame(p, bg=T.SURFACE)
        self._scroll.pack(fill="both", expand=True)
        self._models_root = self._scroll.body
        # One download at a time across both sections: ("whisper", size) or
        # ("ollama", tag) or None.
        self._downloading = None
        self._dl_frac = 0.0
        self._dl_status = ""
        self._dl_bar = None
        self._dl_label = None
        self._installing = False
        self._install_line = ""
        self._probe = None  # cached model state; filled by a worker thread
        self._refresh_models_tab()   # shows a "Loading..." placeholder instantly
        self._reprobe()

    def _reprobe(self):
        """Check model state off the UI thread, then re-render."""
        threading.Thread(target=self._do_probe, daemon=True).start()

    def _do_probe(self):
        if om.is_installed() and not om.is_running():
            om.ensure_running()  # wake it if asleep
        installed = om.is_installed()
        running = installed and om.is_running()
        data = {
            "whisper_dl": wm.downloaded_sizes(),
            "installed": installed,
            "running": running,
            "tags": om.list_installed() if running else [],
        }
        self._probe = data
        try:
            self.after(0, self._refresh_models_tab)
        except Exception:
            pass

    def _refresh_models_tab(self):
        for w in self._models_root.winfo_children():
            w.destroy()
        root = self._models_root

        if self._probe is None:
            tk.Label(root, text="Loading models…", bg=T.SURFACE, fg=T.MUTED,
                     font=T.font(10)).pack(anchor="w", pady=12)
            return

        whisper_dl = self._probe["whisper_dl"]
        installed = self._probe["installed"]
        running = self._probe["running"]
        installed_tags = self._probe["tags"]

        # ===== Section 1: Transcription (Whisper) =====================
        self._subheader(root, "Transcription",
                        "The model that turns recorded speech into text.")
        for m in wm.CATALOG:
            self._render_whisper_row(root, m, m["size"] in whisper_dl)

        # ===== Section 2: Note generation (Ollama) ====================
        tk.Frame(root, bg=T.SURFACE, height=14).pack()
        self._subheader(root, "Note generation",
                        "The local model that writes your meeting notes.")

        banner = tk.Frame(root, bg=T.CARD)
        banner.pack(fill="x", pady=(2, 8))
        inner = tk.Frame(banner, bg=T.CARD)
        inner.pack(fill="x", padx=14, pady=10)
        if self._installing:
            tk.Label(inner, text="Installing Ollama…", bg=T.CARD, fg=T.INK,
                     font=T.semi(10)).pack(anchor="w")
            tk.Label(inner, text=self._install_line or "Starting…", bg=T.CARD,
                     fg=T.MUTED, font=T.font(9)).pack(anchor="w")
        elif not installed:
            tk.Label(inner, text="Ollama isn't installed yet", bg=T.CARD,
                     fg=T.INK, font=T.semi(10)).pack(anchor="w")
            tk.Label(inner, text="Ollama runs note-writing models locally. "
                     "Install it once to enable AI notes.", bg=T.CARD,
                     fg=T.MUTED, font=T.font(9), wraplength=480,
                     justify="left").pack(anchor="w")
            T.AccentButton(inner, "Install Ollama", self._install_ollama,
                           bg=T.CARD).pack(anchor="w", pady=(8, 0))
        elif not running:
            tk.Label(inner, text="Starting Ollama…", bg=T.CARD, fg=T.INK,
                     font=T.semi(10)).pack(anchor="w")
        else:
            row = tk.Frame(inner, bg=T.CARD)
            row.pack(anchor="w")
            dot = tk.Canvas(row, width=10, height=10, bg=T.CARD,
                            highlightthickness=0, bd=0)
            dot.pack(side="left", padx=(0, 6))
            dot.create_oval(1, 1, 9, 9, fill=T.GREEN, outline=T.GREEN)
            tk.Label(row, text="Ollama is ready", bg=T.CARD, fg=T.GREEN,
                     font=T.semi(10)).pack(side="left")

        seen = set()
        for m in om.CURATED:
            self._render_ollama_row(root, m["tag"], m["label"], m["size"],
                                    m["desc"], installed_tags, running)
            seen.add(m["tag"])
        for tag in installed_tags:
            if tag in seen or (tag.endswith(":latest") and tag[:-7] in seen):
                continue
            self._render_ollama_row(root, tag, tag, "", "Already on your machine.",
                                    installed_tags, running)

    def _subheader(self, parent, title, subtitle):
        tk.Label(parent, text=title, bg=T.SURFACE, fg=T.INK,
                 font=T.head(12)).pack(anchor="w", pady=(2, 0))
        tk.Label(parent, text=subtitle, bg=T.SURFACE, fg=T.MUTED, font=T.font(9),
                 wraplength=540, justify="left").pack(anchor="w", pady=(0, 8))

    def _model_card(self, parent, title, size, desc):
        row = tk.Frame(parent, bg=T.WHITE, highlightbackground=T.BORDER,
                       highlightthickness=1)
        row.pack(fill="x", pady=4)
        inner = tk.Frame(row, bg=T.WHITE)
        inner.pack(fill="x", padx=14, pady=10)
        left = tk.Frame(inner, bg=T.WHITE)
        left.pack(side="left", fill="x", expand=True)
        trow = tk.Frame(left, bg=T.WHITE)
        trow.pack(anchor="w")
        tk.Label(trow, text=title, bg=T.WHITE, fg=T.INK,
                 font=T.semi(10)).pack(side="left")
        if size:
            tk.Label(trow, text="  ·  " + size, bg=T.WHITE, fg=T.MUTED,
                     font=T.med(9)).pack(side="left")
        if desc:
            tk.Label(left, text=desc, bg=T.WHITE, fg=T.MUTED, font=T.font(9),
                     wraplength=380, justify="left").pack(anchor="w")
        right = tk.Frame(inner, bg=T.WHITE)
        right.pack(side="right")
        return right

    def _in_use_badge(self, right):
        row = tk.Frame(right, bg=T.WHITE)
        row.pack(anchor="e", pady=4)
        dot = tk.Canvas(row, width=10, height=10, bg=T.WHITE,
                        highlightthickness=0, bd=0)
        dot.pack(side="left", padx=(0, 6))
        dot.create_oval(1, 1, 9, 9, fill=T.GREEN, outline=T.GREEN)
        tk.Label(row, text="In use", bg=T.WHITE, fg=T.GREEN,
                 font=T.semi(10)).pack(side="left")

    def _dl_widgets(self, right):
        self._dl_bar = ttk.Progressbar(right, length=130, mode="determinate",
                                       maximum=100)
        self._dl_bar.pack(anchor="e")
        self._dl_label = tk.Label(right, text="Starting…", bg=T.WHITE,
                                  fg=T.MUTED, font=T.font(8))
        self._dl_label.pack(anchor="e")

    # ---- whisper rows ----
    def _render_whisper_row(self, parent, m, downloaded):
        selected = self.v_model.get() == m["size"]
        right = self._model_card(parent, m["label"], m["human"], m["desc"])
        if self._downloading == ("whisper", m["size"]):
            self._dl_widgets(right)
        elif downloaded:
            if selected:
                self._in_use_badge(right)
            else:
                T.GhostButton(right, "Use",
                              lambda s=m["size"]: self._use_whisper(s),
                              bg=T.WHITE).pack(anchor="e")
        else:
            btn = T.GhostButton(right, "Download",
                                lambda s=m["size"]: self._download_whisper(s),
                                bg=T.WHITE, icon="download")
            btn.pack(anchor="e")
            if self._downloading:
                btn.set_enabled(False)

    # ---- ollama rows ----
    def _is_installed_tag(self, tag, installed_tags):
        want = tag if ":" in tag else tag + ":latest"
        return want in installed_tags or tag in installed_tags

    def _render_ollama_row(self, parent, tag, label, size, desc, installed_tags, running):
        is_inst = self._is_installed_tag(tag, installed_tags)
        selected = self.v_summary.get() in (tag, tag.split(":")[0])
        right = self._model_card(parent, label, size, desc)
        if self._downloading == ("ollama", tag):
            self._dl_widgets(right)
        elif is_inst:
            if selected:
                self._in_use_badge(right)
            else:
                T.GhostButton(right, "Use", lambda t=tag: self._use_ollama(t),
                              bg=T.WHITE).pack(anchor="e")
        else:
            btn = T.GhostButton(right, "Download",
                                lambda t=tag: self._download_ollama(t),
                                bg=T.WHITE, icon="download")
            btn.pack(anchor="e")
            if not running or self._downloading:
                btn.set_enabled(False)

    # ---- selection ----
    def _use_whisper(self, size):
        self.v_model.set(size)
        self._refresh_models_tab()

    def _use_ollama(self, tag):
        self.v_summary.set(tag)
        self._refresh_models_tab()

    # ---- Ollama install ----
    def _install_ollama(self):
        if self._installing:
            return
        self._installing = True
        self._install_line = "Starting…"
        self._refresh_models_tab()
        threading.Thread(target=self._do_install, daemon=True).start()

    def _do_install(self):
        def on_line(line):
            self._install_line = line
            try:
                self.after(0, self._refresh_models_tab)
            except Exception:
                pass
        ok = om.install_ollama(on_line=on_line)
        if ok:
            om.ensure_running()
        try:
            self.after(0, lambda: self._install_done(ok))
        except Exception:
            pass

    def _install_done(self, ok):
        self._installing = False
        self._reprobe()

    # ---- downloads (shared) ----
    def _download_whisper(self, size):
        if self._downloading:
            return
        self._downloading = ("whisper", size)
        self._refresh_models_tab()
        threading.Thread(target=self._do_dl_whisper, args=(size,), daemon=True).start()

    def _do_dl_whisper(self, size):
        try:
            wm.download(size, on_progress=self._progress)
            err = None
        except Exception as e:
            err = str(e)
        try:
            self.after(0, lambda: self._dl_done(("whisper", size), err))
        except Exception:
            pass

    def _download_ollama(self, tag):
        if self._downloading:
            return
        self._downloading = ("ollama", tag)
        self._refresh_models_tab()
        threading.Thread(target=self._do_dl_ollama, args=(tag,), daemon=True).start()

    def _do_dl_ollama(self, tag):
        try:
            om.pull_model(tag, on_progress=self._progress)
            err = None
        except Exception as e:
            err = str(e)
        try:
            self.after(0, lambda: self._dl_done(("ollama", tag), err))
        except Exception:
            pass

    def _progress(self, frac, status):
        if frac is not None:
            self._dl_frac = frac
        self._dl_status = status
        try:
            self.after(0, self._update_dl_ui)
        except Exception:
            pass

    def _update_dl_ui(self):
        if self._dl_bar is not None:
            try:
                self._dl_bar["value"] = int(self._dl_frac * 100)
                self._dl_label.configure(
                    text=f"{self._dl_status}  {int(self._dl_frac * 100)}%")
            except Exception:
                pass

    def _dl_done(self, key, err):
        self._downloading = None
        self._dl_bar = None
        self._dl_label = None
        self._dl_frac = 0.0
        if not err:
            kind, ident = key
            if kind == "whisper":
                self.v_model.set(ident)
            else:
                self.v_summary.set(ident)
        self._reprobe()
        if err:
            from tkinter import messagebox
            messagebox.showinfo("Download", "Could not download %s:\n\n%s"
                                % (key[1], err))

    # ---- AI Notes tab ------------------------------------------------
    def _build_notes(self, p):
        self._section(p, "AI notes prompt",
                      "The instructions sent to the local model. Keep the "
                      "{transcript} placeholder — it's replaced with the meeting.")
        # Reset button reserved at the bottom; the editor fills the space above.
        T.GhostButton(p, "Reset to default", self._reset_prompt,
                      bg=T.SURFACE).pack(side="bottom", anchor="w", pady=(10, 0))
        box = tk.Frame(p, bg=T.WHITE, highlightbackground=T.BORDER,
                       highlightthickness=1)
        box.pack(side="top", fill="both", expand=True, pady=(10, 0))
        self.txt_prompt = tk.Text(box, font=T.font(10), bg=T.WHITE, fg=T.INK_SOFT,
                                  relief="flat", wrap="word", padx=14, pady=12,
                                  bd=0, highlightthickness=0, height=8,
                                  insertbackground=T.INK, spacing3=3)
        self.txt_prompt.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(box, command=self.txt_prompt.yview)
        sb.pack(side="right", fill="y")
        self.txt_prompt.configure(yscrollcommand=sb.set)
        self.txt_prompt.insert("1.0", config.SUMMARY_PROMPT)

    def _reset_prompt(self):
        self.txt_prompt.delete("1.0", "end")
        self.txt_prompt.insert("1.0", self._prompt_default)

    # ---- Projects tab ------------------------------------------------
    def _build_projects(self, p):
        self._section(p, "Projects",
                      "Give each project its own folder. Pick one in the "
                      "sidebar to file that meeting there.")
        T.GhostButton(p, "Add project", self._add_project_row, bg=T.SURFACE,
                      icon="plus").pack(anchor="w", pady=(12, 10))
        scroll = T.ScrollFrame(p, bg=T.SURFACE)
        scroll.pack(fill="both", expand=True)
        self._proj_holder = scroll.body
        self._empty_hint = None

        for proj in self._projects:
            self._add_project_row(proj)
        if not self._projects:
            self._show_empty_hint()

    def _show_empty_hint(self):
        self._empty_hint = tk.Label(
            self._proj_holder, text="No projects yet — add one above.",
            bg=T.SURFACE, fg=T.SUBTLE, font=T.font(10))
        self._empty_hint.pack(anchor="w", pady=6)

    def _add_project_row(self, proj=None):
        if hasattr(self, "_empty_hint") and self._empty_hint:
            self._empty_hint.destroy()
            self._empty_hint = None
        proj = proj if isinstance(proj, dict) else {"name": "", "path": ""}
        row = tk.Frame(self._proj_holder, bg=T.WHITE,
                       highlightbackground=T.BORDER, highlightthickness=1)
        row.pack(fill="x", pady=4)
        inner = tk.Frame(row, bg=T.WHITE)
        inner.pack(fill="x", padx=12, pady=10)

        v_name = tk.StringVar(value=proj.get("name", ""))
        v_path = tk.StringVar(value=proj.get("path", ""))

        top = tk.Frame(inner, bg=T.WHITE)
        top.pack(fill="x")
        tk.Label(top, text="Name", bg=T.WHITE, fg=T.MUTED, width=6,
                 anchor="w", font=T.font(9)).pack(side="left")
        T.entry(top, v_name, width=24).pack(side="left", padx=(6, 0))
        rm = tk.Label(top, text="Remove", bg=T.WHITE, fg=T.RECORD,
                      font=T.semi(9), cursor="hand2")
        rm.pack(side="right")

        bottom = tk.Frame(inner, bg=T.WHITE)
        bottom.pack(fill="x", pady=(8, 0))
        tk.Label(bottom, text="Folder", bg=T.WHITE, fg=T.MUTED, width=6,
                 anchor="w", font=T.font(9)).pack(side="left")
        T.entry(bottom, v_path).pack(side="left", fill="x", expand=True,
                                     padx=(6, 8))

        def browse():
            chosen = filedialog.askdirectory(initialdir=v_path.get() or ".")
            if chosen:
                v_path.set(chosen)
        T.GhostButton(bottom, "Browse", browse, bg=T.WHITE).pack(side="left")

        entry = {"frame": row, "name": v_name, "path": v_path}
        self._proj_rows.append(entry)
        rm.bind("<Button-1>", lambda e, en=entry: self._remove_project_row(en))

    def _remove_project_row(self, entry):
        entry["frame"].destroy()
        self._proj_rows.remove(entry)
        if not self._proj_rows:
            self._show_empty_hint()

    # ---- shared widgets ---------------------------------------------
    def _section(self, parent, title, subtitle):
        tk.Label(parent, text=title, bg=T.SURFACE, fg=T.INK,
                 font=T.head(12)).pack(anchor="w")
        tk.Label(parent, text=subtitle, bg=T.SURFACE, fg=T.MUTED, font=T.font(9),
                 justify="left", wraplength=540).pack(anchor="w", pady=(1, 0))

    def _path_row(self, parent, var):
        row = tk.Frame(parent, bg=T.SURFACE)
        row.pack(fill="x", pady=(8, 18))
        T.entry(row, var).pack(side="left", fill="x", expand=True)
        def browse():
            chosen = filedialog.askdirectory(initialdir=var.get() or ".")
            if chosen:
                var.set(chosen)
        T.GhostButton(row, "Browse", browse, bg=T.SURFACE).pack(
            side="left", padx=(10, 0))

    # --------------------------------------------------------------- save
    def _save(self):
        projects = []
        for r in self._proj_rows:
            name = r["name"].get().strip()
            if not name:
                continue
            projects.append({"name": name, "path": r["path"].get().strip()})

        # Blank folder fields fall back to the portable built-in defaults.
        config.save_settings({
            "whisper_model": self.v_model.get(),
            "summary_model": self.v_summary.get().strip() or config.DEFAULTS["summary_model"],
            "recordings_dir": self.v_rec.get().strip() or config.DEFAULT_RECORDINGS_DIR,
            "transcripts_dir": self.v_tx.get().strip() or config.DEFAULT_TRANSCRIPTS_DIR,
            "summary_prompt": self.txt_prompt.get("1.0", "end").strip() or config.DEFAULT_SUMMARY_PROMPT,
            "projects": projects,
        })
        if self.on_saved:
            self.on_saved()
        self.destroy()

    def _center_on(self, parent):
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        x = px + (pw - w) // 2
        y = py + (ph - h) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
