# DESIGN.md — YapYapYap design system

The single source of truth for YapYapYap's look and feel. All tokens live in
`yapyapyap/ui/theme.py`; this document explains the intent so new UI stays consistent.
The platform is **Tkinter** (canvas-drawn widgets), so colors are hex and "CSS" concepts
(spacing, type ramp, motion) are expressed as Python constants and helper functions.

## Color strategy: Committed (yellow-led)
Signal yellow is the identity and carries the left rail and primary actions. Everything else is a
warm, low-chroma neutral family so the yellow stays the only loud thing on screen.

| Role | Token | Hex | Use |
|---|---|---|---|
| Brand / rail | `YELLOW` | `#FFDE21` | Left rail fill, primary buttons |
| Brand hover | `YELLOW_HOVER` | `#FFD400` | Hover on yellow primary |
| Canvas | `BG` | `#FFEC97` | Soft yellow canvas (minor) |
| List surface | `SURFACE` | `#FFFBE6` | List column, settings body, cards, chips |
| Paper | `PAPER` | `#FFFEFB` | Reader / document background |
| Ink | `INK` | `#1A1A17` | Primary text, the ink button |
| Ink soft | `INK_SOFT` | `#3A352B` | Body copy, secondary ink |
| Muted | `MUTED` | `#7A7150` | Secondary text |
| Subtle | `SUBTLE` | `#AC9F6E` | Tertiary / placeholder |
| Record | `RECORD` | `#E5484D` | Recording dot, Stop |
| Amber | `AMBER` | `#B8860B` | Processing / in-progress |
| Green | `GREEN` | `#1E9E57` | Success / ready / done |

**Rule: never `#000` or `#fff` for text or surfaces.** Neutrals are tinted warm (toward the brand
hue). The pre-blended translucents (`RAIL_PILL`, `RAIL_ACTIVE`, `REC_TINT`, `HOVER_ROW`, …) exist
because Tk has no alpha; they are real rgba values composited onto their host surface. When you need a
"transparent" tint, add a pre-blended constant rather than guessing a hex.

### Contrast (WCAG, documented in theme.py)
Body and heading text on `SURFACE`/`PAPER`/`YELLOW` must clear **AA (4.5:1)**. `MUTED` is the lightest
token allowed for meaningful text; `SUBTLE` is placeholder/decorative only and must not carry
information a user needs to read. See `theme.py` `CONTRAST` notes.

## Typography
Two families, loaded privately at import (fallback: Segoe UI / system).
- **Display / wordmark:** Bricolage Grotesque ExtraBold (`brand()`), Bricolage Grotesque (`head()`).
- **Everything else:** Hanken Grotesk at four weights — `font()` 400, `med()` 500, `semi()` 600,
  `bold()` 700.

**Named type ramp** (in `theme.py` as the `Type` scale; sizes are Tk points). Use these names, not raw
numbers, so hierarchy stays consistent and a single edit re-tunes the whole app:

| Name | Family/weight | pt | Use |
|---|---|---|---|
| `DISPLAY` | Bricolage ExtraBold | 22 | Wordmark, the big timer |
| `H1` | Bricolage 700 | 16 | Screen titles |
| `H2` | Bricolage 700 | 13 | Section headers |
| `H3` | Hanken SemiBold | 11 | Card titles, sub-heads |
| `BODY` | Hanken 400 | 10 | Default body |
| `LABEL` | Hanken Medium | 10 | Buttons, controls |
| `CAPTION` | Hanken 400 | 9 | Secondary / metadata |
| `MICRO` | Hanken Bold | 7 | All-caps eyebrows |

Hierarchy comes from **scale + weight contrast** (≥1.25 between steps), not color alone. Cap reading
columns (notes/transcript) at a comfortable measure; do not let them run full window width.

## Spacing & radius
A 4px base scale, exposed as `SPACE` in `theme.py`. Use the named steps instead of magic paddings:
`XS=4, SM=8, MD=12, LG=16, XL=24, XXL=32`. Vary spacing for rhythm — do not pad everything equally.
Corner radius scale `RADIUS`: `SM=8` (chips/inputs), `MD=11` (buttons), `LG=14` (cards), pill = half
height (segmented control, rail pills).

## Elevation
Tk has no shadow. Elevation is expressed with hairline borders (`BORDER`, `BORDER_DEEP`) and the
button "lip" (a 2px darker bottom edge on primary buttons). Popovers use a 1px ink frame as a soft
shadow line. Do not fake drop shadows with stacked frames.

## Motion
Motion tokens live in `theme.py` as `MOTION` (durations in ms, all tween steps ease out):
- `FAST=120` (hover/press feedback), `BASE=200` (state transitions), `SLOW=320` (view changes),
  `PULSE=1000` (recording-dot breathing cycle).
- Ease out only (no bounce/elastic). The recording pulse is the one continuous animation; everything
  else is a short, intentional transition. Respect a reduced-motion preference (`MOTION.reduced`).

## Components (all in `theme.py`)
- **Buttons:** `AccentButton` (yellow primary + lip), `InkButton` (strong secondary), `GhostButton`
  (quiet, hairline). All share `RoundedButton` with hover/disabled and now a **keyboard-focus ring**.
- **`IconButton`** — rounded-square line-icon button (copy/share/etc.).
- **`SegmentedTabs`** — `[Notes | Transcript]` pill control.
- **`Icon` / `draw_icon`** — 1.7px line-icon set drawn on canvas.
- **`Popover`** — white rounded menu (labels, items, separators, danger items).
- **`SearchField` / `entry`** — white field, hairline border, ink focus ring.
- **`ScrollFrame`** — vertical scroll container.

### Component laws
- Focusable canvas controls show a visible focus ring (keyboard a11y) and respond to Return/Space.
- Cards are used only where they are the right affordance; never nest cards.
- State coverage is mandatory: every interactive surface designs its hover, active, disabled,
  focus, empty, loading, and error states. No raw Tk dialogs for app errors.

## Copy
Plain, calm, privacy-forward. **No em dashes** in UI copy (use commas, colons, periods, parentheses).
Every label earns its place; no restated headings. Long operations always say what is happening.
