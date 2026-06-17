# YapYapYap

A simple, fully-local meeting recorder and transcriber for Windows. Hit one
button to record, hit it again to stop, and YapYapYap captures **both your
microphone and the system audio** (everyone else on the call), transcribes it
**on your own machine** (no cloud, no API key), and - if you've set up a local
LLM - turns the transcript into clean notes.

Everything stays on your computer.

---

## Run it

From the project root:

```powershell
python -m yapyapyap
```

Or install it once (`pip install -e .`) and just run `yapyapyap`.

A window opens with:

- A big **Start recording** button, with a **Project picker** beside it (see
  Projects below). It turns red and reads **Stop recording** while recording,
  with a live timer.
- After you press Stop, a **live progress view** shows exactly what's happening
  (saving → mixing → loading the model → transcribing, with a running %) and the
  **transcript appears line by line as it's produced**.
- **Generate AI meeting notes** - once a conversation has a transcript, a button
  turns it into structured notes (summary, key points, decisions, next steps)
  using a local model. The notes stream in live, just like the transcript.
- A list of **past conversations** on the left - click one to read its notes and
  transcript on the right.
- **Minimise while recording** and a little **floating bird** appears - it
  pulses to show it's recording, sits on top of every other window, can be
  dragged anywhere, glows when you hover, and clicking it brings the app back.
- A **cog icon** (top-right) that opens **Settings** - every configurable option
  lives there.

> **Why does transcription take a few seconds?** Each recording is transcribed in
> a fresh isolated process (this is what keeps the app from crashing), so the
> Whisper model is loaded each time - the "Loading the … model" step. The very
> first run also downloads the model. Smaller models (`tiny`/`base`) load and run
> faster; pick one in Settings.

Prefer the terminal? There's a command-line version too:

```powershell
python -m yapyapyap.apps.cli                 # press ENTER to start, ENTER again to stop
python -m yapyapyap.apps.cli --list          # list past conversations
python -m yapyapyap.apps.cli --model small   # use a more accurate (slower) model this run
```

There's also an optional system-tray version: `python -m yapyapyap.apps.tray`.

> **First run is slow:** Whisper downloads its model (a few hundred MB) the first
> time, then caches it. Later runs are quick.

---

## Settings (the cog icon)

Everything you can configure is in the in-app **Settings** window - no need to
edit code. It has three tabs:

**General**
- **Transcription model** - `tiny` / `base` / `small` / `medium` (speed vs.
  accuracy).
- **Recordings folder** - master history; every conversation is saved here.
- **Default transcripts folder** - where the tidy copy goes when no project is
  selected.

**AI Models** - manage the local model used for notes, no terminal needed:
- If Ollama (the local model runner) isn't installed, an **Install Ollama**
  button sets it up for you.
- Then browse a shortlist of good models (with **size + description**), hit
  **Download** (a progress bar shows the download), and the model becomes
  usable. The one marked **● In use** is what writes your notes; click **Use** on
  any installed model to switch.

**AI Notes**
- The **prompt** used to generate notes is fully editable here (keep the
  `{transcript}` placeholder). A *Reset to default* button restores it.

**Projects**
- Add/remove **projects**, each with its own name and folder.

Changes are saved to `settings.json` and take effect on your next recording /
next time you generate notes.

---

## Projects

If you juggle several workstreams (say *Adeo* and *Risk Engine*), add them under
**Settings → Projects**, each pointing at its own folder. Then:

- Pick a project from the **dropdown next to Start recording** before you record.
- That conversation's **transcript and AI notes are copied into the project's
  folder**, and the **project name is included in the file names**.
- Your **Conversations history still shows everything**, regardless of project,
  with the project name shown next to each entry.

Leave the picker on **(No project)** to use the default transcripts folder.

---

## AI meeting notes

After a conversation is transcribed, click **✨ Generate AI meeting notes**. Using
your local model and the (editable) prompt from Settings, it writes a structured
set of notes - summary, key discussion points, decisions, and action items /
next steps - streamed in live. Notes are saved next to the recording and copied
into the conversation's project folder.

Already have notes? The **↻ regenerate** button (top-right of the Notes tab)
re-runs generation with your latest prompt, overwriting the existing notes -
handy after you tweak the prompt in Settings. Notes are always written in English,
even when the meeting is partly in another language.

This runs on a local model via **Ollama**. The first time, go to **Settings → AI
Models**, install Ollama (one click) and download a model - then it just works.
If you click Generate before that's set up, the app tells you exactly what to do.

---

## What you get per conversation

**The recordings folder** - full output (the master history):

- `meeting_<timestamp>[__<project>].wav` - the mixed audio (you + everyone else)
- `meeting_<timestamp>[__<project>]_transcript.txt` - timestamped transcript
- `meeting_<timestamp>[__<project>]_notes.md` - AI notes *(once you generate them)*

**The project folder (or default transcripts folder)** - a tidy copy of the
transcript (and notes) per conversation, named like:

```
2026-06-09_1432 - Adeo - quick budget sync.txt
```

That's the date, the time, the project (if any), and a max-5-word AI summary.
(Without Ollama, the summary falls back to the first few words spoken, so files
are always named sensibly.)

---

## One-time setup

Install **Python 3.10+** ([python.org](https://www.python.org/downloads/), tick
**"Add Python to PATH"**). Then, in this folder:

```powershell
pip install -r requirements.txt
```

> `PyAudioWPatch` provides the system-audio (WASAPI loopback) capture. If pip
> can't find it: `python -m pip install --upgrade pip` first.

### AI notes (local model)

You don't need to set anything up by hand: open **Settings → AI Models**, click
**Install Ollama**, then **Download** a model. (If you'd rather do it yourself:
install Ollama from <https://ollama.com/download> and `ollama pull llama3.2`.)
It runs quietly in the background and the app detects it automatically. Without
it you still get full transcripts - just no AI notes.

---

## How it fits together

```
yapyapyap/                     the application package
  __main__.py                  `python -m yapyapyap` opens the window     <- run me
  config.py                    settings + defaults (reads/writes settings.json)
  applog.py                    logging setup (writes logs/yapyapyap.log)
  assets/                      bird logo (png/ico) + bundled Sora & Outfit fonts

  apps/
    cli.py                     the command-line version
    tray.py                    the optional system-tray version
    diagnose.py                troubleshooting: tests transcription in isolation

  core/
    engine.py                  orchestrates recording + transcription + AI notes
    recorder.py                low-level mic + system-audio capture (WASAPI loopback)
    mixer.py                   resamples both streams to 16 kHz mono and mixes them
    transcribe.py              in-process speech-to-text helper (used by diagnose)
    summarize.py               AI notes + 5-word titles via local Ollama (streaming)

  managers/
    ollama_manager.py          install Ollama + download/list note-writing models
    whisper_manager.py         download/list transcription (Whisper) models

  ui/
    gui.py                     the main window
    theme.py                   the brand: yellow palette, Sora + Outfit fonts, widgets
    floating.py                the draggable, always-on-top recording indicator (the bird)
    settings_window.py         the Settings dialog (cog icon)

  workers/                     subprocesses (see below)
    recorder_worker.py         streams mic + system audio to disk as it records
    process_worker.py          mixes the stems + transcribes with faster-whisper
    stream_worker.py           transcribes in the background while recording
    whisper_dl_worker.py       downloads a Whisper model in a subprocess

  tools/
    make_logo.py               generates the bird logo into assets/

settings.json / logs / recordings / transcripts   live at the project root
```

### Why workers run in separate processes

On Windows, the audio-capture library (PortAudio) and the speech-to-text engine
(ctranslate2) each load their own native OpenMP runtime. Once a WASAPI capture
stream has been opened in a process, running Whisper in that **same** process -
or even just spawning a subprocess from it - crashes with a hard native segfault
and no Python error. (That was the old "crash when I press Stop" bug.)

The fix is strict process isolation: the app's window process never opens an
audio stream or loads Whisper itself. It launches worker subprocesses for
recording and for transcription, so the two native runtimes are never in the
same process and can't collide.

### Never losing a recording

Audio is **streamed straight to disk as it's captured** (never buffered in
memory), so memory stays flat no matter how long the meeting runs, and a partial
recording always survives. Each stream's `.wav` header is re-flushed and fsync'd
every few seconds (a checkpoint), so even a crash or power-loss leaves a valid,
playable file — losing at most a couple of seconds. On the next launch the app
notices any recording a previous session was cut off on and offers to finish
transcribing it (see `engine.find_interrupted` / `recover`).

### Transcribing while you record (fast Stop)

`stream_worker.py` is a long-lived process that loads Whisper once (using the
configured, accurate model) and transcribes the audio **as it is recorded**,
reading the growing stems on disk. By the time you press Stop most of the meeting
is already transcribed, so finishing only needs the short remaining tail — Stop
is quick even with a slow, accurate model. When you press Stop the worker is told
to "finalize": it transcribes whatever tail is left, writes the mixed `.wav`
archive and the final transcript, and exits. It's best-effort — if it can't start
(e.g. the model isn't downloaded yet) or fails, Stop transparently falls back to a
single full mix + transcribe pass (`process_worker`), so a recording is never at
risk. Because the transcript is stitched from windows rather than one pass, it can
differ very slightly from a single-shot transcription, but uses the same model.

The CPU budget adapts to the machine and always leaves headroom, so it stays
usable on modest laptops as well as big workstations: while recording it uses
about half the cores (so the meeting app and the recording stay smooth); after
Stop it uses more but still leaves a core free (see
`config.background_cpu_threads` / `config.foreground_cpu_threads`).

---

## Logs & troubleshooting

Every run writes to **`logs/yapyapyap.log`**.

- **"Could not find a loopback device"** - set Windows sound output to your
  normal speakers/headphones (some Bluetooth setups confuse it) and try again.
- **No system audio captured** - make sure sound is actually playing through the
  default Windows output device while recording.
- **Anything else** - check `logs/yapyapyap.log` and run `python -m yapyapyap.apps.diagnose`.

---

## A note on consent

Recording conversations is subject to consent laws that vary by country and
region - and several places (Spain, the EU, the UK) treat this seriously. This
tool is for personal/learning use. If you point it at real client or colleague
meetings, tell participants and get their agreement first.
