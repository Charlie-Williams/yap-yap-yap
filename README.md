# YapYapYap

A simple, fully-local meeting recorder and transcriber for **Windows and
macOS**. Hit one button to record, hit it again to stop, and YapYapYap captures
**both your microphone and the system audio** (everyone else on the call),
transcribes it **on your own machine** (no cloud, no API key), and - if you've
set up a local LLM - turns the transcript into clean notes.

Everything stays on your computer.

> **Platform note.** System-audio capture works differently per OS. On **Windows**
> it's automatic (WASAPI loopback). On **macOS** there is no built-in loopback,
> so you install a small free virtual audio device (BlackHole) once and route
> your output through it - see [macOS setup](#macos-setup) below.

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

Install **Python 3.10-3.12** ([python.org](https://www.python.org/downloads/)).

> **Pick 3.10-3.12, not 3.13/3.14.** Transcription uses `faster-whisper`
> (`ctranslate2`), which only ships wheels for these versions. On a newer Python,
> `pip install` will fail to find a wheel.

### Windows setup

Tick **"Add Python to PATH"** during install. Then, in this folder:

```powershell
pip install -r requirements.txt
```

> `PyAudioWPatch` provides the system-audio (WASAPI loopback) capture. If pip
> can't find it: `python -m pip install --upgrade pip` first.

### macOS setup

```bash
# (recommended) use a venv on the right Python
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` installs `sounddevice` (the macOS audio backend) automatically;
`PyAudioWPatch` is skipped on macOS.

**Capturing system audio (the other people on the call).** macOS has no built-in
loopback, so you give it one once:

1. **Install BlackHole** (a free virtual audio device):
   `brew install blackhole-2ch` (or download from
   <https://existential.audio/blackhole/>). Reboot if prompted.
2. **Create a Multi-Output Device** so you still *hear* the call while it's also
   sent to BlackHole: open **Audio MIDI Setup** (in /Applications/Utilities),
   click **+ → Create Multi-Output Device**, and tick **both** your normal
   speakers/headphones **and** BlackHole 2ch.
3. **Set your Mac's output to that Multi-Output Device** (System Settings →
   Sound → Output, or the menu-bar volume control) before recording.

YapYapYap auto-detects the BlackHole input for system audio and your default
microphone for your own voice. (Got a different virtual device? Set
`YAPYAPYAP_LOOPBACK_DEVICE` to part of its name.)

> **No BlackHole yet? Recording still works.** If no loopback device is found,
> YapYapYap records **microphone only** rather than refusing - so an in-person
> meeting (laptop mic in the room) is captured fully. For remote calls you'll
> only get your own voice until you set up BlackHole as above.

> **Permissions.** The first time you record, macOS asks to grant **Microphone**
> access to your terminal / Python - allow it. (System audio via BlackHole needs
> no screen-recording permission.)

### AI notes (local model)

You don't need to set anything up by hand: open **Settings → AI Models**, click
**Install Ollama**, then **Download** a model. On **macOS** this uses Homebrew
(`brew install ollama`); on **Windows** it uses winget. (Prefer to do it
yourself? Install Ollama from <https://ollama.com/download> - or
`brew install ollama` on a Mac - and `ollama pull llama3.2`.) It runs quietly in
the background and the app detects it automatically. Without it you still get
full transcripts - just no AI notes.

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
    recorder.py                low-level mic + system-audio capture (WASAPI loopback on Windows, sounddevice/BlackHole on macOS)
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
    live_worker.py             live captions while recording (auto-fallback)
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

### Live captions while recording

`live_worker.py` is a long-lived process that loads Whisper once and transcribes
the growing audio on disk in near-real-time, so captions appear as people speak.
It uses the smallest downloaded model for speed; when you press Stop a single
clean pass over the whole recording produces the authoritative transcript. If the
machine can't keep up (it measures its own real-time factor), it prints
`@FALLBACK`, the live captions pause, and you simply get the full transcript on
Stop — the recording itself is never affected.

macOS (CoreAudio) doesn't suffer that particular segfault, but the app keeps the
exact same process-isolation architecture on every platform - it's robust, keeps
the UI responsive during transcription, and means there's only one code path to
reason about.

---

## Logs & troubleshooting

Every run writes to **`logs/yapyapyap.log`**.

**Windows**
- **"Could not find a loopback device"** - set Windows sound output to your
  normal speakers/headphones (some Bluetooth setups confuse it) and try again.
- **No system audio captured** - make sure sound is actually playing through the
  default Windows output device while recording.

**macOS**
- **"Could not find a system-audio (loopback) input device"** - BlackHole isn't
  installed or isn't visible. Install it (`brew install blackhole-2ch`) and make
  sure it appears in **Audio MIDI Setup**.
- **No system audio captured** - your Mac's **Output** must be set to the
  **Multi-Output Device** that includes BlackHole while recording (see
  [macOS setup](#macos-setup)). If output goes straight to your speakers,
  BlackHole receives nothing.
- **No microphone captured / silent your-voice track** - grant **Microphone**
  permission to your terminal/Python in System Settings → Privacy & Security →
  Microphone.

**Either OS**
- **Anything else** - check `logs/yapyapyap.log` and run `python -m yapyapyap.apps.diagnose`.

---

## A note on consent

Recording conversations is subject to consent laws that vary by country and
region - and several places (Spain, the EU, the UK) treat this seriously. This
tool is for personal/learning use. If you point it at real client or colleague
meetings, tell participants and get their agreement first.
