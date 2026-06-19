# PRODUCT.md — YapYapYap

register: product

## Product purpose
YapYapYap is a privacy-first desktop app that records a meeting (system audio + microphone),
transcribes it **locally** with faster-whisper, and generates structured AI meeting notes **locally**
via Ollama. Nothing leaves the machine: no cloud, no account, no upload. It runs on Windows and macOS
as a single Tkinter window plus a small floating recording indicator.

## Users
- Knowledge workers, researchers, founders, and privacy-conscious professionals who take a lot of
  calls and want notes without sending audio to a third party.
- People on locked-down or air-gapped machines where cloud transcription is not an option.
- Comfort level: not necessarily technical. The app must work out of the box (it auto-downloads the
  smallest models on first run) and never expose model/plumbing jargon as a barrier.

## Tone & voice
- Calm, plain-spoken, trustworthy. The app handles sensitive audio, so copy reassures without
  nagging. Confident, not chirpy. No exclamation-point energy, no marketing fluff inside the app.
- Privacy is a feature stated quietly and consistently ("Stays on your device"), never as a popup.

## Brand
- **Identity color:** signal yellow `#FFDE21` — a bold, committed "workspace rail" down the left edge.
  This is a *committed* color strategy: yellow carries a large share of the chrome, not a 10% accent.
- **Surfaces:** warm cream list column (`#FFFBE6`), near-white "paper" reading surface (`#FFFEFB`),
  near-black ink text (`#1A1A17`). High contrast, friendly, premium.
- **Type:** Bricolage Grotesque (display / wordmark / big timer) + Hanken Grotesk (everything else).
- **Personality:** friendly utility. Approachable but precise; a tool you trust with private audio.

## Strategic principles
1. **Privacy is the product.** Every screen should make "this stays local" feel obviously true.
2. **Zero-config first run.** A new user records and gets notes without touching settings.
3. **Honest feedback.** Recording, transcribing, and generating are long operations; never show dead
   air or fake progress. Always say what is happening and that it is local.
4. **The recording moment is the hero.** Capturing audio is the core act; that state earns the most
   craft (motion, legibility, the floating indicator when minimized).
5. **Stay out of the way.** This is a tool, not a destination. Quiet chrome, content forward.

## Anti-references (what to avoid)
- Generic SaaS dashboard look: hero-metric cards, identical icon+heading+text card grids, gradient
  accents, "dark because tools look cool dark."
- Cloud-note-app clutter (Otter/Fireflies-style busy timelines).
- Any treatment that reads as "AI made that": templated card walls, em-dashes in copy, fake
  skeleton-everything, neon-on-black.

## Register note
This is a **product** surface (an app/tool): design SERVES the task. Restrained-to-committed color,
strong information hierarchy, low cognitive load, fast comprehension. The yellow identity is the one
deliberate exception to "restrained" — it is the brand and is used with intent.
