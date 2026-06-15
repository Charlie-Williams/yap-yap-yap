# YapYapYap — Visual Redesign Spec (PRD)

A complete design specification for rebuilding YapYapYap's UI in the **"Workspace
Rail" (Direction B)** direction. This document is written for an engineer/agent
implementing against the existing Python + Tkinter codebase (`gui.py`,
`theme.py`, `settings_window.py`).

Every screen referenced here has a matching reference render in **`images/`**.
An interactive, explorable version of all screens lives in
**`YapYapYap Platform.html`** (pan/zoom canvas).

---

## 0. What this is

YapYapYap is a **fully-local meeting recorder → transcriber → AI-notes** desktop
app for Windows. One button records mic + system audio; everything is transcribed
and summarised on-device. The brand is a cheerful **yellow** with a chick mascot.

**Goal of this redesign:** keep the bold yellow identity and the playful mascot,
but make the app feel **clean, premium, light, and effortless to use** — through a
calmer information architecture, a real type system, consistent spacing, and
polished components.

### What changes
- New **three-pane "workspace rail"** layout (replaces the stacked header + record
  bar + two panes).
- New **premium type pairing**: Bricolage Grotesque + Hanken Grotesk (replaces
  Sora + Outfit).
- A consistent **token system** (color / type / spacing / radius / elevation).
- Redrawn components: record control, conversation cards, reader, settings, menus.
- Refined live states (recording, processing, generating) as first-class screens.

### What stays
- The yellow brand palette (extended, not replaced).
- The chick mascot, front and centre.
- The whole feature set and flow: record → transcribe (live) → generate notes
  (live) → browse history; projects; local models in Settings.
- Strict process isolation, local-only privacy posture, all existing copy intent.

---

## 1. Layout architecture

The app is **one window**, default **1080 × 720** (min 900 × 620). Custom-chromed:
the app paints its own title bar region; OS window controls (min / max / close)
sit top-right of the reader pane.

Three columns, left → right:

| Region | Width | Background | Role |
|---|---|---|---|
| **Rail** | 252 px (fixed) | `YELLOW` | Brand, the record control, project picker, navigation, privacy footer |
| **List column** | 304 px (fixed) | `SURFACE` | "All conversations": search, sort, the conversation cards |
| **Reader pane** | fill (min 0) | `PAPER` | Top bar (tabs + actions + window controls) and the document area |

Dividers between regions are 1px hairlines (`YELLOW_DEEP` on the rail edge,
`BORDER` elsewhere). The window has a 16px outer radius and a soft drop shadow
when floating (OS decides in practice).

Reference: `images/01-main-idle.png`.

---

## 2. Design tokens

### 2.1 Color

Keep the existing `theme.py` constant names where they exist; add the new ones.

| Token | Hex | Usage |
|---|---|---|
| `YELLOW` | `#FFDE21` | Brand. Rail fill, primary highlights, title bar |
| `YELLOW_HOVER` | `#FFD400` | Hover on yellow primary |
| `YELLOW_DEEP` | `#E7C400` | Borders/dividers sitting **on** yellow |
| `BG` | `#FFEC97` | Soft yellow canvas (used behind floating doc; minor in B) |
| `SURFACE` | `#FFFBE6` | List column, settings body, cards, chips |
| `PAPER` | `#FFFEFB` | Reader/document background (warm near-white) |
| `CARD` | `#FBEFA6` | Inactive chip / segmented-control track |
| `BORDER` | `#EFDD83` | Hairline borders on light surfaces |
| `BORDER_DEEP` | `#E4CE72` | Stronger hairline (checkbox outline, etc.) |
| `SOFT` | `#FFE05C` | **Selection** highlight (selected conversation card) |
| `INK` | `#1A1A17` | Primary text, the ink/black button |
| `INK_SOFT` | `#3A352B` | Body copy, secondary ink |
| `MUTED` | `#7A7150` | Secondary text (warm) |
| `SUBTLE` | `#AC9F6E` | Tertiary / placeholder |
| `RECORD` | `#E5484D` | Recording red (dot, Stop button) |
| `AMBER` | `#B8860B` | Processing / in-progress |
| `GREEN` | `#1E9E57` | Success, "ready", completed steps |
| `WHITE` | `#FFFFFF` | Inputs, popovers, icon-button fills |

**On-yellow hairline** (pills/dividers inside the yellow rail): `rgba(120,90,20,0.18)`.
**On-yellow translucent fill** (rail pills/cards): `rgba(255,255,255,0.40)`
(0.35 for the privacy footer).

Accent colors share intent: amber = working, green = done, red = recording. Never
introduce new hues — vary only via these.

### 2.2 Typography

Two families. **Replace Sora/Outfit.** Bundle static TTFs into `assets/fonts/`
exactly as the app already bundles fonts (see §9.1).

- **Display** — `Bricolage Grotesque` — wordmark, all headings, the big timer.
  Weights: 700 (headings), 800 (wordmark).
- **UI / body** — `Hanken Grotesk` — everything else. Weights: 400 / 500 / 600 / 700.

| Role | Family / weight | Size (px) | Notes |
|---|---|---|---|
| Wordmark "YapYapYap" | Bricolage 800 | 20 (rail) / 30 (large) | tri-tone, letter-spacing −0.5 |
| Reader H1 (note/transcript title) | Bricolage 700 | 26–27 | letter-spacing −0.5, line-height 1.15 |
| Pane / column title ("All conversations") | Bricolage 700 | 18 | |
| Section title (Settings, panels) | Bricolage 700 | 15–16 | |
| Big timer (recording) | Bricolage 700 | 64 | tabular-nums |
| Body copy | Hanken 400–500 | 14.5–15.5 | line-height 1.55–1.62, `INK_SOFT` |
| Conversation title | Hanken 600 | 14.5 (13.5 compact) | 1-line, ellipsis |
| Meta / timestamps | Hanken 500 | 11.5–12.5 | `MUTED`, tabular-nums for durations |
| **Section label** (SUMMARY, KEY DISCUSSION…) | Hanken 700 | 11.5 | UPPERCASE, letter-spacing 0.9px, `MUTED`, + 7px yellow square bullet |
| Buttons / tabs / nav | Hanken 600–700 | 13–15 | |
| Tiny labels (TRANSCRIPT ONLY, field labels) | Hanken 600 | 10.5–12 | |

Wordmark tri-tone: `Yap`=`INK`, `Yap`=`#6B5E3A`, `Yap`=`INK`.

### 2.3 Spacing, radius, elevation

- **Spacing scale** (px): 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 34.
  Panels pad 16–24; reader doc pads 34 × 44.
- **Radius** (px): chips/pills `999`; buttons/cards `10–14`; panels/windows `16`;
  small swatches `2`; checkbox `5`.
- **Elevation** (use sparingly — light, warm shadows, never grey):
  - Card/panel: `0 1px 2px rgba(60,45,10,.05), 0 12px 28px -16px rgba(60,45,10,.22)`
  - Popover/menu: `0 12px 36px rgba(45,33,8,.22), 0 0 0 1px rgba(45,33,8,.06)`
  - Floating window: `0 30px 80px -24px rgba(45,33,8,.45), 0 10px 30px rgba(45,33,8,.14)`
  - Button "lip" (yellow): `0 2px 0 rgba(180,140,10,.35), 0 6px 16px rgba(200,160,20,.28)`
  - Button "lip" (ink): `0 2px 0 rgba(0,0,0,.25), 0 6px 16px rgba(0,0,0,.22)`

  > Tkinter note: real box-shadows aren't available. Approximate with a 1px
  > border + the existing rounded-canvas widgets; keep the "lip" by drawing a
  > 2px darker bottom edge. Elevation is a *nice-to-have*, hierarchy comes from
  > the borders and fills.

### 2.4 Iconography

Line icons, **1.7px stroke**, round caps/joins, 24-viewBox, `currentColor`. Set
used: home, folder, gear, search, mic, plus, lock, copy, export(share), download,
chevron-down/right, kebab (⋯), sparkle (notes), check. No emoji. The sparkle
(✨ "Generate notes") becomes a clean 4-point star, not the emoji.

---

## 3. Components

### 3.1 Window chrome
Custom title region. OS controls (minimize line, maximize square, close ×) live
**top-right of the reader pane**, 44 × 30 hit targets, `INK_SOFT` glyphs, close
hovers red. On the Settings window and the slim title bars they sit on the yellow
bar (`INK`).

### 3.2 Rail (`YELLOW`, 252px) — `images/01-main-idle.png`
Top → bottom, padded 20 × 16:
1. **Brand**: mascot (34px) + wordmark (20px), gap 10.
2. **Record control** (full-width) — see §3.3.
3. **Project picker** — full-width pill, `rgba(255,255,255,.40)` fill,
   on-yellow hairline: `[■ square] No project … [▾]`. Opens the project menu
   (§3.13). 22px gap below.
4. **Nav** (items 9 × 12, radius 10; active = `rgba(255,255,255,.55)` fill +
   on-yellow hairline, label 700):
   - `⌂ All conversations` (active by default)
   - `▣ Projects ▾` → indented children, each `[■ amber] <name>` (Adeo, Risk Engine)
   - `⚙ Settings` (opens Settings window)
5. Spacer.
6. **Privacy footer** — `rgba(255,255,255,.35)` card, lock icon + "Everything
   stays on this PC" (11.5/600/`INK_SOFT`).

### 3.3 Record control (the heart of the app)
One full-width control in the rail, three states:

| State | Fill | Label | Sub-line (centered, below) |
|---|---|---|---|
| **idle** | `INK` | ● `RECORD` dot + "Start recording" (white) | — |
| **recording** | `RECORD` | ■ white square + "Stop recording" (white) | ● pulsing red + "Recording · MM:SS" (`INK_SOFT`, tabular) |
| **processing** | `rgba(26,26,23,.35)` (disabled) | ● faded + "Start recording" | ● amber + "Transcribing… 47%" (`AMBER`) |

The button is **never plain grey**; disabled = washed brand/ink. Refs:
`images/02-main-recording.png`, `images/03-main-processing.png`.

> Decision captured: in Direction B the idle record button is **ink/black** (the
> single clearest primary against the yellow rail). Recording → red, processing →
> faded-ink. If you prefer yellow-forward, swap idle fill to `YELLOW` + `INK`
> text — but ink tested as the cleaner read here.

### 3.4 List column (`SURFACE`, 304px) — `images/01-main-idle.png`
- Header pad 20 × 16: title "All conversations" (Bricolage 18), then **search
  field** (white, 38px, search icon + placeholder), then a row: "N conversations"
  (left, `SUBTLE`) · "Newest ▾" (right, `MUTED`).
- **Conversation cards** (list, pad 0 × 8):
  - Default: transparent; **selected**: `SOFT` fill + `YELLOW_DEEP` 1px border,
    radius 12.
  - Content: **title** (600, 1-line ellipsis) → **meta** one line:
    `Date · Time • Duration` (11.5/500/`MUTED`, **never wraps**) → **tag row**:
    project tag (`[■ amber] Name` in `AMBER`/600) or "No project" (`SUBTLE`); plus
    `TRANSCRIPT ONLY` (10.5/600/`SUBTLE`) when there's no notes yet.
  - Trailing **⋯** kebab (top-right of card) opens the conversation menu (§3.13).
- **Recording item**: while recording, a special top card — `rgba(229,72,77,.08)`
  fill, red hairline, pulsing dot, "Recording…" + "MM:SS · No project"
  (`images/02-main-recording.png`).
- **Empty**: "No conversations yet" + helper line (`images/07-main-welcome.png`).

### 3.5 Reader pane top bar (56px)
Left: **tabs** segmented pill `[Notes][Transcript]` — active = white pill +
subtle shadow, inactive `MUTED`; track is `CARD` w/ `BORDER`. Only show tabs that
have content; hide the bar entirely during recording/processing/generating.
Right: icon buttons **Copy**, **Export(share)**, a 1px divider, then the **OS
window controls**.

### 3.6 Notes reader — `images/01-main-idle.png`
Document, pad 34 × 44, max-width ~620 centered. Markdown → styled blocks:
- **H1** title (Bricolage 700/27) + meta line: `Date · Time • [project tag] • Duration`.
- For each section: a **section label** (UPPERCASE tracked + yellow square bullet),
  then content:
  - `## Summary` → paragraph (15.5/1.62).
  - `## Key discussion points` → bullets: 6px amber dot + text (14.5/1.55).
  - `## Decisions` → if "None…", render italic `MUTED`.
  - `## Action items / next steps` → **checkbox rows**: 16px rounded-square
    outline (`BORDER_DEEP`) + task text. (Strip the `- [ ] Owner —` markdown into
    a clean checkbox + sentence.)
  - `## Open questions` → bullets.
- Markdown cleanup rules (keep from current `_insert_md`): drop `**`/`_` emphasis
  markers; only render a heading when it has real content (the prompt already
  enforces "no empty sections").

### 3.7 Transcript reader — `images/05-main-transcript.png`
H1 + meta, then timestamped lines: `[m:ss]` (12.5/600/`SUBTLE`, tabular, 34px
gutter) + segment text (15/1.6/`INK_SOFT`). Active tab = Transcript.

### 3.8 Recording view (reader) — `images/02-main-recording.png`
Centered hero: a **REC** pill (red, pulsing dot), the **big timer** (Bricolage
64, tabular), a **waveform** strip (thin rounded bars, ink with occasional amber,
quiet bars `BORDER`), the line "Listening to your microphone and this PC's audio",
and two **source chips** "Microphone" / "System audio" each with a green level
dot. (Replaces the old text-only status.)

### 3.9 Processing view (reader) — `images/03-main-processing.png`
H1 "Processing your conversation", then a **step list**:
- done step = green check in a soft green disc + label (`MUTED`).
- active step = amber spinner ring + label (`INK`, 700) + right-aligned `%`.
- Steps (live, from the worker): Saved the recording → Mixed microphone + system
  audio → Loaded the *<Model>* model → Transcribing the audio (with %).
- A thin **progress bar** (amber on `CARD`, max-width 520) under the steps.
- **"Transcript so far"** section label, then live lines `[m:ss] text…`; the last
  two lines are emphasised (`INK`/600), earlier ones `MUTED`; a blinking amber
  caret trails the newest line. (Preserve the existing streaming behaviour.)

### 3.10 Generating-notes view (reader) — `images/04-main-generating.png`
H1 (the conversation title) + meta, an amber **"✦ Writing notes…"** pill (pulsing
star), then the notes stream in using the §3.6 styles. The in-progress tail shows
a blinking caret; not-yet-written sections show **shimmer** placeholder lines
(`CARD`→`#FFF6CF` sweep). Preserve token-streaming.

### 3.11 Generate-CTA view — `images/06-main-generate-cta.png`
When a conversation has a transcript but **no notes**: centered card — yellow
rounded sparkle tile, "Turn this into clean notes", helper line, the primary
**"✦ Generate AI meeting notes"** button (yellow + ink), and a tiny lock line
"Runs locally with <model> · nothing leaves your PC". (If the transcript is too
short, keep the existing instant short-note path — no spinner.)

### 3.12 Welcome / first-run — `images/07-main-welcome.png`
Empty list + reader: mascot (72px), "Ready when you are", helper pointing to the
rail's Start recording, and a 3-step row (1 Record / 2 Transcribe / 3 AI notes)
as small `SURFACE` cards with numbered yellow chips. If the first-run model
download is happening, show a slim amber banner ("Downloading the Base model
(one-time)…") at the top of the reader.

### 3.13 Context menus — `images/12-menu-conversation.png`, `images/13-menu-project.png`
White popover, radius 11, menu shadow, 5px pad, items 13.5/500/`INK_SOFT`,
hover `rgba(26,26,23,.05)`, 7px row radius. A leading 7px slot shows a filled
`INK` dot for the current selection.
- **Conversation ⋯**: "Assign to project ▸" (flyout: ● No project / Adeo / Risk
  Engine) — separator — "Hide from list" — **"Delete from computer"** (`RECORD`,
  hover red-tint). Keep the existing two-step delete confirm.
- **Project picker** (rail): ● No project / [■] Adeo / [■] Risk Engine —
  separator — "＋ Manage projects…" (`MUTED`, opens Settings → Projects).

### 3.14 Settings window — `images/08…11-settings-*.png`
Separate dialog, **720 × 600**, radius 16. Slim yellow title bar (mascot +
"Settings" + window controls). **Tab bar** under it: `General · AI Models · AI
Notes · Projects`; active = `INK`/700 + 2.5px `YELLOW_DEEP` underline; inactive
`MUTED`. Body pad 22 × 24. Sticky footer (border-top): **Cancel** (ghost) +
**Save** (yellow primary), right-aligned.

- **General** (`08`): intro line pointing to AI Models; "Recordings folder" +
  helper + path field + folder Browse button; "Default transcripts folder" + path
  field + Browse.
- **AI Models** (`09`): **Transcription** subhead + Whisper cards
  (Tiny 75 MB / Base 145 MB / Small 480 MB / Medium 1.5 GB) each with size + desc
  and a right action: **● In use** (green dot) / **Use** (ghost) /
  **⤓ Download** (ghost). Then **Note generation** subhead + an Ollama status
  banner (green "Ollama is ready" / or "not installed yet" + Install Ollama) +
  Ollama cards (Llama 3.2 3B / 1B / Mistral 7B …) with the same actions. Use the
  real catalogs from `whisper_manager.CATALOG` / `ollama_manager.CURATED`.
- **AI Notes** (`10`): "AI notes prompt" + helper (keep `{transcript}`), a large
  editor box showing `DEFAULT_SUMMARY_PROMPT`, and a **Reset to default** ghost
  button below.
- **Projects** (`11`): "Projects" + helper, **＋ Add project** ghost, then project
  rows — each a card with a Name field, a Folder field + Browse, and a **Remove**
  (red) action.

Shared field style: white, 40px, radius 10, 1px `BORDER`, focus ring `INK`/yellow.

---

## 4. Interaction & state rules

- **Single source of truth = record state** (`idle / starting / recording /
  processing`). The rail control, the list "recording" item, the reader, and the
  window all reflect it. Disable Start while processing/generating; never grey
  it to a dead state.
- **Tabs** appear only for content that exists; default to Notes if present, else
  Transcript. Hide tabs entirely in live states.
- **Selecting** a conversation loads its notes (or transcript) into the reader and
  updates the kebab/menu affordances.
- **Live streaming** for both transcription and notes must remain (text appears as
  produced). The shimmer/caret are cosmetic only.
- **Errors** (mic/loopback failure, model missing, Ollama not set up) surface as a
  calm inline banner in the reader or a dialog — match the existing copy, restyled
  to the tokens. "Generate" before Ollama is set up should explain the one-click
  fix in Settings → AI Models.

---

## 5. Copy guidelines
Keep the existing voice: friendly, plain, reassuring about privacy. Sentence case
everywhere except the UPPERCASE section labels. Use "this PC" (Windows). Durations
as `Xm Ys` / `Xs` / `Hh Mm`. Dates as `Jun 10, 2026 · 12:46 PM`. Never invent
content in notes (the prompt enforces this; the UI must render "no notes yet" and
short-note states gracefully).

---

## 6. Per-screen reference index

| # | Screen | File |
|---|---|---|
| 01 | Main — idle, viewing notes | `images/01-main-idle.png` |
| 02 | Main — recording | `images/02-main-recording.png` |
| 03 | Main — processing / transcribing | `images/03-main-processing.png` |
| 04 | Main — generating AI notes | `images/04-main-generating.png` |
| 05 | Main — transcript view | `images/05-main-transcript.png` |
| 06 | Main — has transcript, no notes (CTA) | `images/06-main-generate-cta.png` |
| 07 | Main — first run / empty | `images/07-main-welcome.png` |
| 08 | Settings — General | `images/08-settings-general.png` |
| 09 | Settings — AI Models | `images/09-settings-models.png` |
| 10 | Settings — AI Notes | `images/10-settings-notes.png` |
| 11 | Settings — Projects | `images/11-settings-projects.png` |
| 12 | Menu — conversation ⋯ | `images/12-menu-conversation.png` |
| 13 | Menu — project picker | `images/13-menu-project.png` |

---

## 7. Implementation notes (Tkinter)

The redesign maps cleanly onto the current architecture — it's a **re-skin + a
layout change**, not a rewrite.

### 7.1 Fonts
Add static TTFs to `assets/fonts/` and load them the same way `theme._load_bundled_fonts()`
already does:
- **Bricolage Grotesque** — ship `Bricolage Grotesque 24pt` static instances at
  700 and 800 (the variable font won't register cleanly on Windows GDI).
- **Hanken Grotesk** — ship 400 / 500 / 600 / 700.
Update `theme.py` family constants:
`BRAND_FAMILY = "Bricolage Grotesque"` (use the 800 face for the wordmark),
`HEAD_FAMILY = "Bricolage Grotesque"`, `UI_FAMILY = "Hanken Grotesk"`,
plus medium/semibold faces. Keep the graceful fallback to Segoe UI.

### 7.2 `theme.py`
- Replace the palette block with §2.1 (most names already exist — add `PAPER`,
  `INK_SOFT`, `BORDER_DEEP`, `SOFT` if missing; you already have `YELLOW_SOFT`
  ≈ `SOFT`).
- Extend `RoundedButton` to support the three record states and the "lip" bottom
  edge. Add a `SegmentedTabs` widget (Notes/Transcript), a `Pill`/`Chip` widget,
  a `MenuPopover`, and a `Card` frame helper.
- Icons: render the line-icon set as small vector glyphs (Tkinter: draw on a
  `Canvas`, or pre-render PNGs into `assets/icons/` at 1×/2×). The mascot already
  exists (`assets/logo_*.png`).

### 7.3 `gui.py`
- Rebuild `_build_ui` as the **three-pane rail layout** (§1). The rail hosts the
  record control, project picker, nav, and privacy footer. The middle column is
  the existing conversation list, restyled to §3.4. The right pane is the reader
  with the new top bar.
- Map existing methods onto the new chrome: `on_toggle`/`_set_state` drive the
  §3.3 record control + the list "recording" item; `_render_processing`,
  `_render_notes_generating`, `_render_conversation` feed the §3.8–3.10 / 3.6–3.7
  reader bodies; `_conv_menu` / project picker → §3.13 popovers.
- Keep all worker/process-isolation logic untouched.

### 7.4 `settings_window.py`
- Re-skin to §3.14: yellow title bar, underline tabs, token fields, the model
  cards (drive from `whisper_manager.CATALOG` / `ollama_manager.CURATED`,
  preserving the In use / Use / Download / Install states and the live download
  progress), the prompt editor, and the project rows. Footer Cancel/Save.

### 7.5 Don't regress
Process isolation, atomic settings writes, portable folder handling, first-run
model download, two-step delete, and all privacy/consent behaviour stay exactly
as they are. This is a visual + IA pass.

---

## 8. Asset checklist
- [ ] `assets/fonts/` — Bricolage Grotesque (700, 800) + Hanken Grotesk (400/500/600/700) static TTFs.
- [ ] Mascot PNGs — already present (`logo_32…256.png`); reuse.
- [ ] Line-icon set (home, folder, gear, search, mic, plus, lock, copy, share, download, chevrons, kebab, sparkle, check) as glyphs or `assets/icons/` PNGs.
- [ ] Reference renders — `images/01…13`.
- [ ] Living spec — `YapYapYap Platform.html` (interactive, all screens).
