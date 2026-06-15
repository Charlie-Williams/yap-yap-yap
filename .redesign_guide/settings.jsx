// settings.jsx — the Settings window (separate dialog) with its four tabs:
// General, AI Models, AI Notes, Projects. Each tab is a full settings window.

const { P, DISP, UI, Bird, WinControls, Gear, Plus, Search, Export } = window;

const SET_SHADOW = '0 30px 80px -20px rgba(45,33,8,0.5), 0 12px 30px rgba(45,33,8,0.16)';
const PROMPT = `You are an expert meeting-notes assistant. Below is a transcript of a meeting (it may be rough or contain transcription errors). Write concise, accurate notes in Markdown.

Strict rules:
- Use ONLY information that is actually present in the transcript. Never invent names, numbers, dates, decisions or action items.
- NEVER write placeholders such as "[insert …]", "TBD" or "None specified". If a section has no real content, leave it out entirely.

When there is enough content, use these sections (include a section only when it genuinely has content):

## Summary
2–4 sentences on what was discussed and any outcome.

## Key discussion points
- Concise bullets of the main topics.

## Decisions
- Decisions that were actually made.

## Action items / next steps
- [ ] Owner — the task (add a deadline only if one was clearly stated).

TRANSCRIPT:
{transcript}`;

function PrimaryBtn({ children }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 22px',
      borderRadius: 11, background: P.yellow, border: `1px solid ${P.yellowDeep}`,
      boxShadow: '0 2px 0 rgba(180,140,10,0.3)', fontFamily: UI, fontWeight: 700, fontSize: 14, color: P.ink, whiteSpace: 'nowrap' }}>{children}</span>
  );
}
function GhostBtn({ children, danger = false }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '9px 16px',
      borderRadius: 10, background: P.white, border: `1px solid ${P.border}`,
      fontFamily: UI, fontWeight: 600, fontSize: 13.5, color: danger ? P.record : P.inkSoft, whiteSpace: 'nowrap' }}>{children}</span>
  );
}
function Field({ value, mono = false, flex = false, placeholder }) {
  return (
    <div style={{ flex: flex ? 1 : 'none', minWidth: 0, height: 40, display: 'flex', alignItems: 'center',
      padding: '0 13px', borderRadius: 10, background: P.white, border: `1px solid ${P.border}`,
      fontFamily: UI, fontSize: 13.5, color: value ? P.inkSoft : P.subtle, fontWeight: 500,
      overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{value || placeholder}</div>
  );
}
function SecHead({ title, sub }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontFamily: UI, fontSize: 14.5, fontWeight: 700, color: P.ink, whiteSpace: 'nowrap' }}>{title}</div>
      {sub && <div style={{ fontFamily: UI, fontSize: 12.5, color: P.muted, lineHeight: 1.5, marginTop: 3, maxWidth: 540 }}>{sub}</div>}
    </div>
  );
}

function SettingsWin({ active = 'General', children }) {
  const tabs = ['General', 'AI Models', 'AI Notes', 'Projects'];
  return (
    <div style={{ width: 720, height: 600, borderRadius: 16, overflow: 'hidden', position: 'relative',
      background: P.surface, boxShadow: SET_SHADOW, border: '1px solid rgba(120,90,20,0.2)',
      display: 'flex', flexDirection: 'column' }}>
      {/* titlebar */}
      <div style={{ height: 44, background: P.yellow, borderBottom: `1px solid ${P.yellowDeep}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 0 0 16px', flex: '0 0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <Bird size={20} />
          <span style={{ fontFamily: DISP, fontWeight: 700, fontSize: 15, color: P.ink }}>Settings</span>
        </div>
        <WinControls dark />
      </div>
      {/* tab bar */}
      <div style={{ display: 'flex', gap: 4, padding: '0 22px', background: P.surface,
        borderBottom: `1px solid ${P.border}`, flex: '0 0 auto' }}>
        {tabs.map((t) => {
          const on = t === active;
          return (
            <div key={t} style={{ padding: '14px 10px 12px', position: 'relative', whiteSpace: 'nowrap',
              fontFamily: UI, fontSize: 14, fontWeight: on ? 700 : 600, color: on ? P.ink : P.muted }}>
              {t.replace(/ /g, ' ')}
              {on && <div style={{ position: 'absolute', left: 6, right: 6, bottom: -1, height: 2.5, borderRadius: 2, background: P.yellowDeep }} />}
            </div>
          );
        })}
      </div>
      {/* body */}
      <div style={{ flex: 1, overflow: 'hidden', padding: '22px 24px' }}>{children}</div>
      {/* footer */}
      <div style={{ borderTop: `1px solid ${P.border}`, padding: '14px 22px', display: 'flex',
        justifyContent: 'flex-end', gap: 10, flex: '0 0 auto', background: P.surface }}>
        <GhostBtn>Cancel</GhostBtn>
        <PrimaryBtn>Save</PrimaryBtn>
      </div>
    </div>
  );
}

// ---- model card ----
function InUse() {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontFamily: UI, fontSize: 13, fontWeight: 700, color: P.ink, whiteSpace: 'nowrap' }}>
      <span style={{ width: 8, height: 8, borderRadius: 999, background: P.green }} />{'In use'}
    </span>
  );
}
function MiniBtn({ children, download = false }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px',
      borderRadius: 9, background: P.white, border: `1px solid ${P.border}`,
      fontFamily: UI, fontWeight: 600, fontSize: 13, color: P.inkSoft, whiteSpace: 'nowrap' }}>
      {download && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 4v11M7 11l5 4 5-4M5 20h14"/></svg>}
      {children}
    </span>
  );
}
function ModelCard({ title, desc, action }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 15px',
      borderRadius: 12, background: P.white, border: `1px solid ${P.border}`, marginBottom: 8 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: UI, fontSize: 14, fontWeight: 700, color: P.ink, whiteSpace: 'nowrap' }}>{title}</div>
        <div style={{ fontFamily: UI, fontSize: 12.5, color: P.muted, lineHeight: 1.45, marginTop: 2 }}>{desc}</div>
      </div>
      <div style={{ flex: '0 0 auto' }}>{action}</div>
    </div>
  );
}

// ============================================================ tabs
function GeneralTab() {
  return (
    <div>
      <div style={{ fontFamily: UI, fontSize: 12.5, color: P.muted, lineHeight: 1.5, marginBottom: 22, maxWidth: 560 }}>
        Transcription and note-writing models — including downloads — live on the <b style={{ color: P.inkSoft }}>AI Models</b> tab.
      </div>
      <SecHead title="Recordings folder" sub="Master history — every conversation is saved here." />
      <div style={{ display: 'flex', gap: 10, marginBottom: 24 }}>
        <Field flex value="C:\Users\you\YapYapYap\recordings" />
        <GhostBtn><Folder /></GhostBtn>
      </div>
      <SecHead title="Default transcripts folder" sub="Where the tidy copy goes when no project is selected." />
      <div style={{ display: 'flex', gap: 10 }}>
        <Field flex value="C:\Users\you\YapYapYap\transcripts" />
        <GhostBtn><Folder /></GhostBtn>
      </div>
    </div>
  );
  function Folder() { return <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3.5 6.5h5l2 2.5h10v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 2.5 18V8a1.5 1.5 0 0 1 1.5-1.5z"/></svg>; }
}

function ModelsTab() {
  return (
    <div style={{ height: '100%', overflow: 'hidden' }}>
      <SecHead title="Transcription" sub="The model that turns recorded speech into text." />
      <ModelCard title="Whisper Tiny · 75 MB" desc="Fastest. Fine for clear audio and quick drafts." action={<MiniBtn>Use</MiniBtn>} />
      <ModelCard title="Whisper Base · 145 MB" desc="A good balance of speed and accuracy — sensible default." action={<InUse />} />
      <ModelCard title="Whisper Small · 480 MB" desc="More accurate, especially with accents or crosstalk." action={<MiniBtn download>Download</MiniBtn>} />
      <ModelCard title="Whisper Medium · 1.5 GB" desc="Best accuracy here. Slower; needs more RAM." action={<MiniBtn download>Download</MiniBtn>} />

      <div style={{ height: 14 }} />
      <SecHead title="Note generation" sub="The local model that writes your meeting notes." />
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '11px 14px', borderRadius: 12,
        background: 'rgba(30,158,87,0.1)', border: '1px solid rgba(30,158,87,0.25)', marginBottom: 10 }}>
        <svg width="16" height="16" viewBox="0 0 14 14" fill="none" stroke={P.green} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 7.5L5.5 11L12 3.5"/></svg>
        <span style={{ fontFamily: UI, fontSize: 13.5, fontWeight: 700, color: P.green }}>Ollama is ready</span>
      </div>
      <ModelCard title="Llama 3.2 (3B) · 2.0 GB" desc="Great all-rounder and a sensible default for most machines." action={<InUse />} />
      <ModelCard title="Llama 3.2 (1B) · 1.3 GB" desc="Fastest. Runs well on any laptop; fine for quick notes." action={<MiniBtn>Use</MiniBtn>} />
      <ModelCard title="Mistral (7B) · 4.1 GB" desc="Strong, well-balanced quality. Needs a little more RAM/time." action={<MiniBtn download>Download</MiniBtn>} />
    </div>
  );
}

function NotesTab() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <SecHead title="AI notes prompt" sub="The instructions sent to the local model. Keep the {transcript} placeholder — it's replaced with the meeting." />
      <div style={{ flex: 1, borderRadius: 12, background: P.white, border: `1px solid ${P.border}`,
        padding: '14px 16px', overflow: 'hidden', marginBottom: 12 }}>
        <pre style={{ margin: 0, fontFamily: '"Hanken Grotesk", ui-monospace, monospace', fontSize: 12.5,
          lineHeight: 1.6, color: P.inkSoft, whiteSpace: 'pre-wrap' }}>{PROMPT}</pre>
      </div>
      <div><GhostBtn>Reset to default</GhostBtn></div>
    </div>
  );
}

function ProjectRow({ name, path }) {
  return (
    <div style={{ borderRadius: 12, background: P.white, border: `1px solid ${P.border}`, padding: 14, marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{ fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.muted, width: 46 }}>Name</span>
        <div style={{ width: 200 }}><Field value={name} /></div>
        <div style={{ flex: 1 }} />
        <span style={{ fontFamily: UI, fontSize: 13, fontWeight: 600, color: P.record }}>Remove</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.muted, width: 46 }}>Folder</span>
        <Field flex value={path} />
        <GhostBtn><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3.5 6.5h5l2 2.5h10v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 2.5 18V8a1.5 1.5 0 0 1 1.5-1.5z"/></svg></GhostBtn>
      </div>
    </div>
  );
}
function ProjectsTab() {
  return (
    <div>
      <SecHead title="Projects" sub="Give each project its own folder. Pick one next to the record button to file that meeting there." />
      <div style={{ marginBottom: 16 }}><GhostBtn><Plus s={14} />Add project</GhostBtn></div>
      <ProjectRow name="Adeo" path="C:\Users\you\Work\Adeo\notes" />
      <ProjectRow name="Risk Engine" path="C:\Users\you\Work\RiskEngine\notes" />
    </div>
  );
}

const SettingsGeneral = () => <SettingsWin active="General"><GeneralTab /></SettingsWin>;
const SettingsModels = () => <SettingsWin active="AI Models"><ModelsTab /></SettingsWin>;
const SettingsNotes = () => <SettingsWin active="AI Notes"><NotesTab /></SettingsWin>;
const SettingsProjects = () => <SettingsWin active="Projects"><ProjectsTab /></SettingsWin>;

Object.assign(window, { SettingsWin, SettingsGeneral, SettingsModels, SettingsNotes, SettingsProjects });
