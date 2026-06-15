"""
summarize.py
------------
Turns a raw transcript into clean, structured AI meeting notes, and produces the
short 5-word title used to name files in the transcripts/project folders.

It uses Ollama (https://ollama.com) - a free app that runs LLMs locally - so
everything stays on your machine. The model and the notes prompt are both
configurable in Settings.

To enable AI notes:
  1. Install Ollama for Windows.
  2. Pull a model once, e.g.:  ollama pull llama3.1
  3. Ollama then runs in the background at localhost:11434.
"""

import json
import re
import urllib.request
import urllib.error

from yapyapyap import config

# 127.0.0.1, not "localhost": avoids a ~2s IPv6 stall on Windows.
OLLAMA_BASE = "http://127.0.0.1:11434"
OLLAMA_GENERATE = OLLAMA_BASE + "/api/generate"


def _model(model=None):
    return model or config.SUMMARY_MODEL


def is_available(model=None):
    """Quick check that Ollama is running locally."""
    try:
        req = urllib.request.Request(OLLAMA_BASE + "/api/tags")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except (urllib.error.URLError, OSError):
        return False


_PLACEHOLDER_RE = re.compile(
    r"\[(?:insert|list|e\.?g\.?|note|main topics|owner|deadline|brief|"
    r"decision|topic|name|date|\.\.\.)[^\]]*\]", re.IGNORECASE)
_EMPTY_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s*(?:\[\s*\])?\s*$")
# A checkbox / bullet whose content is filler, e.g. "[ ] None",
# "- [ ] Owner: To be determined, pending discussion."
_CHECKBOX_FILLER_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?\[[ xX]?\]\s*(?:"
    r"|none|n/?a|tbd|nothing\b.*|no\s+\w+.*|"
    r".*(?:to be (?:determined|confirmed|decided|assigned)|tbd|pending|"
    r"not (?:mentioned|specified|determined|yet))\b.*"
    r")\.?\s*$", re.IGNORECASE)
# A whole line that is essentially "X was not mentioned/specified", "TBD", etc.
_NONINFO_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?.{0,70}\b(?:not (?:mentioned|specified|stated|provided|"
    r"determined|discussed|yet (?:determined|decided))|to be (?:determined|"
    r"confirmed|decided)|tbd|pending discussion)\b.*$", re.IGNORECASE)
_FILLER_RE = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:"
    r"tbd|n/?a|none(?:\s+\w+){0,3}|not specified|"
    r"nothing\b.*|"
    r"no (?:decision|action|next step|open question|specific|deadline|further|"
    r"new|additional|other)\w*\b.*"
    r")\.?\s*$", re.IGNORECASE)


_PREAMBLE_RE = re.compile(
    r"^\s*(here (?:are|is)|below (?:are|is)|sure[,!]|certainly[,!]|i(?:'ve| have)|"
    r"these are).{0,80}:\s*$", re.IGNORECASE)


def clean_notes(text):
    """
    Tidy up notes from weaker local models: drop a chatty preamble line, drop any
    line still containing a fill-in-the-blank placeholder, drop empty bullets and
    filler like 'None specified', then remove any heading left with no real
    content under it. Belt-and-braces on top of the prompt rules.
    """
    if not text:
        return text
    lines = text.split("\n")
    # Strip a leading "Here are the meeting notes:" style preamble.
    while lines and (not lines[0].strip() or _PREAMBLE_RE.match(lines[0])):
        if lines[0].strip() and not lines[0].lstrip().startswith("#"):
            lines.pop(0)
        elif not lines[0].strip():
            lines.pop(0)
        else:
            break

    kept = []
    for raw in lines:
        line = raw.rstrip()
        # A line that still has a placeholder means the model failed - drop it.
        if _PLACEHOLDER_RE.search(line):
            continue
        if (_EMPTY_BULLET_RE.match(line) or _FILLER_RE.match(line)
                or _CHECKBOX_FILLER_RE.match(line) or _NONINFO_RE.match(line)):
            continue
        kept.append(line)

    # Remove headings that have no content before the next heading / end.
    out = []
    for i, line in enumerate(kept):
        if line.lstrip().startswith("#"):
            has_content = False
            for nxt in kept[i + 1:]:
                if nxt.lstrip().startswith("#"):
                    break
                if nxt.strip():
                    has_content = True
                    break
            if not has_content:
                continue
        out.append(line)

    # Collapse 3+ blank lines to one.
    result = []
    blanks = 0
    for line in out:
        if line.strip():
            blanks = 0
            result.append(line)
        else:
            blanks += 1
            if blanks <= 1:
                result.append(line)
    return "\n".join(result).strip()


def _build_prompt(transcript, prompt):
    """Insert the transcript into the (editable) prompt template."""
    prompt = prompt or config.SUMMARY_PROMPT
    if "{transcript}" in prompt:
        return prompt.replace("{transcript}", transcript)
    return prompt.rstrip() + "\n\nTRANSCRIPT:\n" + transcript


def summarize(transcript, model=None, prompt=None):
    """
    Return AI notes as a string, or None if Ollama isn't available / fails.
    Non-streaming (used by the CLI).
    """
    if not transcript.strip():
        return None
    model = _model(model)
    if not is_available(model):
        return None

    payload = {"model": model, "prompt": _build_prompt(transcript, prompt),
               "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_GENERATE, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return clean_notes(body.get("response", "").strip()) or None
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None


def summarize_stream(transcript, model=None, prompt=None, on_token=None):
    """
    Stream AI notes from Ollama, calling on_token(chunk) as text arrives.
    Returns the full notes string. Raises SummarizeError on failure.
    """
    if not transcript.strip():
        raise SummarizeError("There's no transcript to summarise yet.")
    model = _model(model)
    if not is_available(model):
        raise SummarizeError(
            "Ollama isn't running. Install it from ollama.com, run "
            "'ollama pull %s', then try again." % model)

    payload = {"model": model, "prompt": _build_prompt(transcript, prompt),
               "stream": True}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(OLLAMA_GENERATE, data=data,
                                 headers={"Content-Type": "application/json"})
    out = []
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw in resp:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    raise SummarizeError(str(obj["error"]))
                chunk = obj.get("response", "")
                if chunk:
                    out.append(chunk)
                    if on_token:
                        on_token(chunk)
                if obj.get("done"):
                    break
    except (urllib.error.URLError, OSError) as e:
        raise SummarizeError("Could not reach Ollama: %s" % e)

    notes = clean_notes("".join(out).strip())
    if not notes:
        raise SummarizeError("The model returned no notes. Is '%s' pulled?" % model)
    return notes


class SummarizeError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# Short title generation (used for the transcripts-folder filenames)
# --------------------------------------------------------------------------

_TITLE_PROMPT = """Give a title of AT MOST 5 words summarising this conversation.
Reply with ONLY the title - no quotes, no punctuation, no explanation.

CONVERSATION:
{transcript}
"""


def safe_filename(text, max_len=60):
    """Strip characters Windows won't allow in a filename and tidy whitespace."""
    text = re.sub(r'[\\/:*?"<>|\n\r\t]', "", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text[:max_len].strip() or "untitled"


def _strip_timestamps(transcript):
    """Remove leading [m:ss] stamps so the heuristic title reads cleanly."""
    return re.sub(r"\[\d+:\d{2}(?::\d{2})?\]\s*", "", transcript)


def short_title(transcript, model=None, max_words=5):
    """
    A <=5-word, filename-safe summary of the conversation. Tries Ollama first;
    falls back to the first few words of speech. Never raises.
    """
    model = _model(model)
    text = (transcript or "").strip()
    if not text:
        return "empty conversation"

    if is_available(model):
        payload = {"model": model,
                   "prompt": _TITLE_PROMPT.format(transcript=text[:6000]),
                   "stream": False}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(OLLAMA_GENERATE, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                title = " ".join(body.get("response", "").split()[:max_words])
                cleaned = safe_filename(title)
                if cleaned and cleaned != "untitled":
                    return cleaned
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            pass

    words = _strip_timestamps(text).split()
    return safe_filename(" ".join(words[:max_words])) if words else "untitled"
