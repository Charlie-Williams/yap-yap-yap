"""
engine.py
---------
The orchestration layer that ties everything together WITHOUT ever loading the
audio and speech-to-text native libraries into the same process.

Background: on Windows, PortAudio (audio capture) and numpy/scipy/ctranslate2
(mixing + Whisper) load conflicting native OpenMP runtimes. A process that has
opened a WASAPI capture stream then segfaults on any further heavy native work.
So the work is split across short-lived subprocesses:

  * Recording          -> recorder_worker.py  (PyAudio + stdlib only)
  * Mixing + transcribe -> process_worker.py   (numpy/scipy/whisper, no audio)

AI notes (summarisation) talk to a local Ollama over HTTP, which is safe to run
in-process, and happen ON DEMAND (see generate_notes), not automatically.

Projects: a RecordingSession can be tied to a project (a name + a folder). The
project name is embedded in the saved file names, and the transcript/notes are
also copied into the project's folder, while the master history under
recordings_dir always contains everything.
"""

import os
import re
import csv
import sys
import subprocess
from datetime import datetime

import config
import summarize
import ollama_manager as om

_HERE = os.path.dirname(os.path.abspath(__file__))
_RECORDER_WORKER = os.path.join(_HERE, "recorder_worker.py")
_PROCESS_WORKER = os.path.join(_HERE, "process_worker.py")

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class EngineError(RuntimeError):
    pass


TOO_SHORT_NOTE = "This conversation was too short to generate meeting notes."


def is_too_short(transcript):
    """True if there's too little speech to meaningfully summarise."""
    spoken = re.sub(r"\[\d+:\d{2}(?::\d{2})?\]", "", transcript or "")
    return len(spoken.split()) < 25


# --------------------------------------------------------------------------
# Project / filename helpers
# --------------------------------------------------------------------------
def project_tag(project):
    """A filesystem-safe tag for a project, embedded in file names."""
    if not project:
        return ""
    name = (project.get("name") or "").strip()
    if not name:
        return ""
    return summarize.safe_filename(name).replace("__", " ").strip()


def parse_base(base):
    """Split a meeting base name into (timestamp_str, project_tag)."""
    name = os.path.basename(base)
    if name.startswith("meeting_"):
        name = name[len("meeting_"):]
    if "__" in name:
        stamp, tag = name.split("__", 1)
    else:
        stamp, tag = name, ""
    return stamp, tag


def resolve_project(base):
    """Return the project dict a conversation belongs to (by its file name)."""
    _, tag = parse_base(base)
    if not tag:
        return None
    for p in config.PROJECTS:
        if project_tag(p) == tag:
            return p
    return {"name": tag, "path": ""}  # project may have been removed


def base_for(stamp, project):
    """The recordings-folder base path for a given timestamp + project."""
    name = "meeting_" + stamp
    tag = project_tag(project)
    if tag:
        name += "__" + tag
    return os.path.join(config.RECORDINGS_DIR, name)


def _new_base(project):
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return stamp, base_for(stamp, project)


def _copy_dir(project):
    """Where the transcript/notes CSV exports should go for this project."""
    if project and project.get("path"):
        return project["path"]
    return config.TRANSCRIPTS_DIR


def camel_case(text):
    """Turn 'Adeo Pipeline Conundrum' into 'adeoPipelineConundrum'."""
    words = re.findall(r"[A-Za-z0-9]+", text or "")
    if not words:
        return "notes"
    return words[0].lower() + "".join(w[:1].upper() + w[1:] for w in words[1:])


def _export_name(stamp, project, label, ext, camel=False):
    """Build "YYYYMMDD_HHMM_[project]_<label>.<ext>" (project omitted if none)."""
    date = stamp[:10].replace("-", "")          # YYYYMMDD
    hhmm = stamp[11:16].replace("-", "")          # HHMM
    parts = [date, hhmm]
    if project and project.get("name"):
        parts.append(summarize.safe_filename(project["name"]))
    parts.append(camel_case(label) if camel else summarize.safe_filename(label))
    return "_".join(parts) + ext


def _csv_name(stamp, project, label):
    return _export_name(stamp, project, label, ".csv")


def _txt_name(stamp, project, label):
    # AI-generated titles are camelCased in the file name.
    return _export_name(stamp, project, label, ".txt", camel=True)


def _unique_path(path):
    """Avoid clobbering an existing file by adding a counter if needed."""
    if not os.path.exists(path):
        return path
    root, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{root} ({n}){ext}"):
        n += 1
    return f"{root} ({n}){ext}"


def write_transcript_csv(stamp, project, transcript, dest_dir):
    """Save the transcript as a CSV of (timestamp, text) rows."""
    os.makedirs(dest_dir, exist_ok=True)
    path = _unique_path(os.path.join(dest_dir, _csv_name(stamp, project, "transcript")))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "text"])
        for line in transcript.split("\n"):
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^\[(\d+:\d{2}(?::\d{2})?)\]\s*(.*)$", line)
            if m:
                w.writerow([m.group(1), m.group(2)])
            else:
                w.writerow(["", line])
    return path


def write_notes_txt(stamp, project, notes, title, dest_dir):
    """Save the AI notes as a plain-text (.txt) file, named with the title."""
    os.makedirs(dest_dir, exist_ok=True)
    path = _unique_path(os.path.join(dest_dir, _txt_name(stamp, project, title)))
    with open(path, "w", encoding="utf-8") as f:
        f.write(notes.strip() + "\n")
    return path


class RecordingSession:
    """Drives one record -> transcribe cycle via subprocesses."""

    def __init__(self, project=None):
        self.project = project
        os.makedirs(config.RECORDINGS_DIR, exist_ok=True)
        os.makedirs(config.TRANSCRIPTS_DIR, exist_ok=True)
        self.stamp, self.base = _new_base(project)
        self.wav = self.base + ".wav"
        self._mic_wav = self.base + ".mic.wav"
        self._sys_wav = self.base + ".sys.wav"
        self._proc = None

    # ---------------------------------------------------------------- record
    def start(self):
        """Launch the recorder subprocess and wait until it is actually live."""
        self._proc = subprocess.Popen(
            [sys.executable, _RECORDER_WORKER, self._mic_wav, self._sys_wav],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, creationflags=_NO_WINDOW,
        )
        line = self._proc.stdout.readline()
        if line.strip() != "READY":
            err = self._proc.stderr.read() if self._proc.stderr else ""
            raise EngineError("Recorder failed to start.\n" + err.strip())

    def stop(self, model_size=None, progress=None):
        """
        Stop recording, then mix + transcribe. Returns a dict describing the
        saved artefacts. Blocking. `progress(kind, value)` (optional) streams
        live status; see _run_transcription for the kinds.
        """
        if self._proc is None:
            raise EngineError("stop() called with no active recording.")

        model_size = model_size or config.WHISPER_MODEL

        def _emit(kind, value=""):
            if progress:
                try:
                    progress(kind, value)
                except Exception:
                    pass

        _emit("step", "Saving the recording")
        try:
            self._proc.stdin.write("stop\n")
            self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        out, err = self._proc.communicate(timeout=120)
        duration = 0.0
        ok = False
        for ln in (out or "").splitlines():
            if ln.startswith("OK"):
                ok = True
                try:
                    duration = float(ln.split()[1])
                except (IndexError, ValueError):
                    pass
        if not ok:
            self._cleanup_stems()
            raise EngineError("Recording failed.\n" + (err or out or "").strip())

        transcript_path = self.base + "_transcript.txt"
        transcript = self._run_transcription(model_size, transcript_path, _emit)
        self._cleanup_stems()

        # Tidy transcript copy into the project (or default transcripts) folder.
        self._save_transcript_copy(transcript)

        _emit("done", "")
        return {
            "base": self.base,
            "wav": self.wav,
            "transcript_path": transcript_path,
            "transcript": transcript,
            "duration": duration,
            "project": self.project,
        }

    def _run_transcription(self, model_size, transcript_path, emit):
        """Launch process_worker and stream its progress events to `emit`.
        Returns the final transcript text (authoritative, read from file)."""
        proc = subprocess.Popen(
            [sys.executable, _PROCESS_WORKER, self._mic_wav, self._sys_wav,
             self.wav, model_size, transcript_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            creationflags=_NO_WINDOW,
        )
        total = 0.0
        log_tail = []
        for raw in proc.stdout:
            line = raw.rstrip("\r\n")
            if not line.startswith("@"):
                if line.strip():
                    log_tail.append(line)
                    del log_tail[:-20]
                continue
            tag, _, val = line[1:].partition(" ")
            if tag == "STEP":
                emit("step", val)
            elif tag == "DUR":
                try:
                    total = float(val)
                except ValueError:
                    total = 0.0
                emit("dur", total)
            elif tag == "SEG":
                end_s, _, text = val.partition("\t")
                try:
                    frac = (float(end_s) / total) if total > 0 else 0.0
                except ValueError:
                    frac = 0.0
                emit("seg", (max(0.0, min(frac, 1.0)), text))
        proc.wait()
        if proc.returncode != 0:
            raise EngineError("Transcription failed (exit %s).\n%s"
                              % (proc.returncode, "\n".join(log_tail).strip()))
        try:
            with open(transcript_path, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return ""

    def cancel(self):
        """Abort a recording without transcribing (best effort)."""
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write("stop\n")
                self._proc.stdin.flush()
                self._proc.communicate(timeout=30)
            except Exception:
                self._proc.kill()
        self._cleanup_stems()

    def _cleanup_stems(self):
        for p in (self._mic_wav, self._sys_wav):
            try:
                os.remove(p)
            except OSError:
                pass

    def _save_transcript_copy(self, transcript):
        try:
            if transcript.strip():
                write_transcript_csv(self.stamp, self.project, transcript,
                                     _copy_dir(self.project))
        except Exception:
            pass  # non-fatal


# --------------------------------------------------------------------------
# AI notes - on demand
# --------------------------------------------------------------------------
def _resolve_summary_model(model=None):
    """
    Decide which local model to use for notes, and make sure Ollama is up.
    Falls back to any installed model if the configured one isn't present, and
    raises a helpful, UI-pointing error if AI notes can't run at all.
    """
    want = model or config.SUMMARY_MODEL

    if not om.is_running():
        if om.is_installed():
            om.ensure_running()  # installed but asleep - wake it
        if not om.is_running():
            if not om.is_installed():
                raise summarize.SummarizeError(
                    "AI notes need a local model. Open Settings - AI Models and "
                    "click Install Ollama, then download a model.")
            raise summarize.SummarizeError(
                "Ollama is installed but not running. Try again in a moment.")

    installed = om.list_installed()
    if not installed:
        raise summarize.SummarizeError(
            "No AI model downloaded yet. Open Settings - AI Models and download "
            "one (e.g. Llama 3.2).")
    if om.is_model_installed(want):
        return want
    return installed[0]  # use whatever the user actually has


def generate_notes(base, on_token=None, model=None, prompt=None):
    """
    Generate AI notes for an existing conversation (identified by its `base`
    path). Streams tokens to on_token(chunk) if given. Saves the notes next to
    the recording AND a tidy copy into the conversation's project folder.

    Returns (notes_path, notes_text). Raises summarize.SummarizeError on
    failure (e.g. Ollama not running).
    """
    tx_path = base + "_transcript.txt"
    try:
        with open(tx_path, encoding="utf-8") as f:
            transcript = f.read().strip()
    except OSError:
        raise summarize.SummarizeError("No transcript found for this conversation.")

    # Too little was said to summarise? Don't ask the model (weak local models
    # will happily hallucinate a whole meeting) - just say so gracefully.
    if is_too_short(transcript):
        notes = TOO_SHORT_NOTE
        if on_token:
            on_token(notes)
    else:
        model = _resolve_summary_model(model)
        notes = summarize.summarize_stream(
            transcript, model=model,
            prompt=prompt or config.SUMMARY_PROMPT, on_token=on_token)

    notes_path = base + "_notes.md"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(notes)

    # Export the notes as a .txt into the project (or default transcripts)
    # folder, named with a short AI summary, and save that title alongside the
    # recording so the conversation list can show it.
    try:
        if not is_too_short(transcript):
            project = resolve_project(base)
            stamp, _ = parse_base(base)
            title = summarize.short_title(transcript, model=config.SUMMARY_MODEL)
            write_notes_txt(stamp, project, notes, title, _copy_dir(project))
            with open(base + "_title.txt", "w", encoding="utf-8") as f:
                f.write(title)
    except Exception:
        pass  # non-fatal

    return notes_path, notes


def export_conversation(base):
    """Re-write the transcript (.csv) and notes (.txt) exports into this
    conversation's project folder - used after its project is changed."""
    project = resolve_project(base)
    stamp, _ = parse_base(base)
    dest = _copy_dir(project)
    tx_path = base + "_transcript.txt"
    if os.path.exists(tx_path):
        with open(tx_path, encoding="utf-8") as f:
            tx = f.read().strip()
        if tx:
            write_transcript_csv(stamp, project, tx, dest)
    notes_path, title_path = base + "_notes.md", base + "_title.txt"
    if os.path.exists(notes_path) and os.path.exists(title_path):
        with open(notes_path, encoding="utf-8") as f:
            notes = f.read().strip()
        with open(title_path, encoding="utf-8") as f:
            title = f.read().strip()
        if title and title.lower() != "too short":
            write_notes_txt(stamp, project, notes, title, dest)


def transcribe_wav(wav_path, model_size=None):
    """Re-transcribe an already-mixed .wav via the isolated process worker."""
    model_size = model_size or config.WHISPER_MODEL
    out_txt = wav_path + ".txt"
    proc = subprocess.run(
        [sys.executable, _PROCESS_WORKER, wav_path, wav_path,
         wav_path + ".remix.wav", model_size, out_txt],
        capture_output=True, text=True, creationflags=_NO_WINDOW,
    )
    if proc.returncode != 0:
        raise EngineError("Transcription failed (exit %s).\n%s\n%s"
                          % (proc.returncode, proc.stdout.strip(), proc.stderr.strip()))
    try:
        with open(out_txt, encoding="utf-8") as f:
            return f.read().strip()
    finally:
        for p in (out_txt, wav_path + ".remix.wav"):
            try:
                os.remove(p)
            except OSError:
                pass
