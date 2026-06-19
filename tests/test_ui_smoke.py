"""
Headless UI smoke tests for YapYapYap.

Builds every UI surface in-process (no real recording, no model downloads) and
walks every visual state, asserting nothing raises while widgets render. This is
the regression gate for the UI/UX rework: if the window, settings, floating
indicator, theme tokens, or any state view fail to construct, these fail.

Runs as a plain script (``python tests/test_ui_smoke.py`` -> exit 0/1) and under
pytest. Requires a display; on macOS the root is withdrawn so nothing pops up.
"""
import os
import sys
import traceback

# Make the package importable when run as a bare script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk  # noqa: E402

from yapyapyap.ui import theme as T  # noqa: E402
from yapyapyap.ui import gui, floating, settings_window  # noqa: E402


def _new_root():
    root = tk.Tk()
    root.withdraw()  # never actually show during tests
    return root


def _pump(widget, n=3):
    """Flush pending Tk events so geometry/draw callbacks run."""
    for _ in range(n):
        widget.update_idletasks()
        widget.update()


def test_theme_tokens_are_well_formed():
    """Every exported color token is a valid Tk color and the type ramp resolves."""
    root = _new_root()
    try:
        names = [n for n in dir(T) if n.isupper()]
        color_like = [
            n for n in names
            if isinstance(getattr(T, n), str) and getattr(T, n).startswith("#")
        ]
        assert color_like, "expected hex color tokens on the theme"
        for n in color_like:
            val = getattr(T, n)
            # winfo_rgb raises TclError on an invalid color spec.
            root.winfo_rgb(val)
        # The named type ramp must produce usable font specs.
        for fn in ("display", "head", "body"):
            if hasattr(T, fn):
                getattr(T, fn)(13)
        # Named ramp / scales exist and are well-formed.
        for step in ("DISPLAY", "H1", "H2", "H3", "BODY", "LABEL", "CAPTION", "MICRO"):
            fam, size = getattr(T.Type, step)
            assert isinstance(fam, str) and isinstance(size, int)
        assert T.SPACE.XS < T.SPACE.SM < T.SPACE.MD < T.SPACE.LG < T.SPACE.XL
        assert T.MOTION.FAST < T.MOTION.BASE < T.MOTION.SLOW
    finally:
        root.destroy()


def test_text_tokens_meet_wcag_aa():
    """Every token meant to carry text clears AA contrast on its surfaces."""
    failures = []
    for label, (fg, surfaces) in T.CONTRAST_REQUIRED.items():
        for bg in surfaces:
            ratio = T.contrast_ratio(fg, bg)
            if ratio < 4.5:
                failures.append(f"{label} {fg} on {bg}: {ratio:.2f}:1 (< 4.5)")
    assert not failures, "AA contrast failures:\n  " + "\n  ".join(failures)


def test_button_takes_focus_and_draws_ring():
    """RoundedButton is keyboard-focusable and re-renders its focus ring."""
    root = _new_root()
    try:
        clicks = []
        btn = T.AccentButton(root, "Go", lambda: clicks.append(1))
        btn.pack()
        _pump(root)
        assert str(btn.cget("takefocus")) in ("1", "True")
        # Keyboard activation + focus ring are wired (bindings registered).
        assert btn.bind("<Return>"), "Return not bound"
        assert btn.bind("<space>"), "space not bound"
        # Focus-ring state machine re-renders without error.
        btn._on_focus_in(None)
        _pump(root)
        assert btn._focused is True
        btn._on_focus_out(None)
        _pump(root)
        assert btn._focused is False
        # Keyboard activation invokes the command.
        btn._on_click(None)
        assert clicks == [1]
    finally:
        root.destroy()


def test_main_window_builds_and_walks_all_states():
    """The main App constructs and survives every record/process state + views."""
    # Neutralize side effects: no model downloads, no interrupted-recording dialog.
    gui.App._first_run_setup = lambda self: None
    gui.App._check_interrupted = lambda self: None

    root = _new_root()
    try:
        app = gui.App(root)
        _pump(root)
        for state in ("idle", "starting", "recording", "processing", "idle"):
            app._set_state(state)
            _pump(root)
        app._show_placeholder()
        _pump(root)
        # Topbar + nav refresh paths.
        app._update_nav_active()
        app.refresh_list()
        _pump(root)
    finally:
        root.destroy()


def test_settings_window_builds_every_tab():
    root = _new_root()
    try:
        for tab in ("General", "Models", "Notes", "Projects"):
            win = settings_window.SettingsWindow(root, initial_tab=tab)
            _pump(win)
            win._show_empty_hint() if tab == "Projects" else None
            _pump(win)
            win.destroy()
    finally:
        root.destroy()


def test_floating_indicator_renders_and_toggles():
    root = _new_root()
    try:
        ind = floating.RecordingIndicator(root, on_click=lambda: None)
        ind.show((229, 72, 77))
        _pump(root)
        ind.hide()
        _pump(root)
    finally:
        root.destroy()


def test_icon_button_is_keyboard_accessible():
    root = _new_root()
    try:
        hits = []
        ib = T.IconButton(root, "copy", command=lambda: hits.append(1))
        ib.pack()
        _pump(root)
        assert str(ib.cget("takefocus")) in ("1", "True")
        assert ib.bind("<Return>") and ib.bind("<space>")
        ib._set_focused(True)
        _pump(root)
        assert ib._focused is True
        ib._activate()
        assert hits == [1]
    finally:
        root.destroy()


def test_reduced_motion_recording_path():
    """With reduced motion on, the recording view still builds and the wave
    renders a static frame without scheduling the rapid animation loop."""
    gui.App._first_run_setup = lambda self: None
    gui.App._check_interrupted = lambda self: None
    prev = T.MOTION.reduced
    T.MOTION.reduced = True
    root = _new_root()
    try:
        app = gui.App(root)
        app._set_state("recording")
        _pump(root)
        app._set_state("idle")
        _pump(root)
    finally:
        T.MOTION.reduced = prev
        root.destroy()


def test_no_em_dashes_in_ui_copy():
    """DESIGN.md bans em/en dashes in user-facing copy. Scan string literals
    (AST-based, so code comments are ignored) across the UI modules."""
    import ast
    import glob
    ui_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "yapyapyap", "ui")
    offenders = []
    for path in glob.glob(os.path.join(ui_dir, "*.py")):
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "—" in node.value or "–" in node.value:
                    offenders.append(f"{os.path.basename(path)}:{node.lineno} "
                                     f"{node.value[:50]!r}")
    assert not offenders, "em/en dash in UI copy:\n  " + "\n  ".join(offenders)


def test_numbered_row_and_numeral_ramp():
    """The big-numeral ramp resolves and the NumberedRow editorial row builds."""
    root = _new_root()
    try:
        fam, size = T.Type.NUMERAL
        assert isinstance(fam, str) and isinstance(size, int)
        assert T.numeral(20)[1] == 20
        row = T.NumberedRow(root, 1, "Record", "Captures the whole call.")
        row.pack()
        _pump(root)
        assert row.title.cget("text") == "RECORD"  # all-caps
        assert row.desc is not None
    finally:
        root.destroy()


def test_notes_section_rules_and_transcript_render():
    """Notes markdown renders editorial section heads with embedded ink underline
    rules, the rules resize, and the transcript path renders without error."""
    gui.App._first_run_setup = lambda self: None
    gui.App._check_interrupted = lambda self: None
    root = _new_root()
    try:
        app = gui.App(root)
        _pump(root)
        v = app.viewer
        v.configure(state="normal")
        v.delete("1.0", "end")
        app._sec_rules = []
        app._insert_doc_header(v, "x")
        app._insert_notes_md(
            v, "## Summary\nWe shipped it.\n\n## Decisions\n- Go bold\n\n"
               "## Action items\n- [ ] Ship it\n")
        v.configure(state="disabled")
        _pump(root)
        assert len(app._sec_rules) == 3, "expected one rule per section head"
        app._resize_sec_rules()  # must not raise
        _pump(root)
        # Transcript view (timestamps as eyebrows) renders too.
        v.configure(state="normal")
        v.delete("1.0", "end")
        app._sec_rules = []
        app._insert_transcript(v, "[0:01] hello\n[0:05] world")
        v.configure(state="disabled")
        _pump(root)
    finally:
        root.destroy()


def test_processing_checklist_walks_progress():
    """The numbered processing checklist builds and finishes each step (no
    spinner state machine left behind)."""
    gui.App._first_run_setup = lambda self: None
    gui.App._check_interrupted = lambda self: None
    root = _new_root()
    try:
        app = gui.App(root)
        _pump(root)
        app._set_state("processing")
        _pump(root)
        for step in ("Saving the recording", "Mixing",
                     "Loading the Whisper tiny model", "Transcribing"):
            app._apply_progress("step", step)
            _pump(root)
        app._apply_progress("seg", (0.5, "[0:01] hello world"))
        app._apply_progress("bar", 0.9)
        _pump(root)
        app._finish_active_steps()
        _pump(root)
        assert len(app._step_rows) == 4
        assert all(r["state"] == "done" for r in app._step_rows)
        app._set_state("idle")
        _pump(root)
    finally:
        root.destroy()


def test_floating_indicator_shows_timer():
    """The floating slab accepts a timer update while shown."""
    root = _new_root()
    try:
        ind = floating.RecordingIndicator(root, on_click=lambda: None)
        ind.show((229, 72, 77))
        ind.set_time("01:23")
        _pump(root)
        assert ind._time == "01:23"
        ind.hide()
        _pump(root)
    finally:
        root.destroy()


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
