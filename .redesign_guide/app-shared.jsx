// app-shared.jsx — palette, sample data, and reusable pieces for the
// YapYapYap main-page direction mockups. Everything is exported to window so
// the per-direction file and the page script can pick pieces up.

const P = {
  yellow: '#FFDE21',
  yellowHover: '#FFD400',
  yellowDeep: '#E7C400',
  bg: '#FFEC97',
  surface: '#FFFBE6',
  card: '#FBEFA6',
  border: '#EFDD83',
  borderDeep: '#E4CE72',
  soft: '#FFE05C',
  ink: '#1A1A17',
  inkSoft: '#3A352B',
  muted: '#7A7150',
  subtle: '#AC9F6E',
  record: '#E5484D',
  amber: '#B8860B',
  green: '#1E9E57',
  white: '#FFFFFF',
  paper: '#FFFEFB',
};

const DISP = '"Bricolage Grotesque", system-ui, sans-serif';
const UI = '"Hanken Grotesk", system-ui, sans-serif';

// ---- sample content (realistic, drawn from the project's own recordings) ----
const CONVERSATIONS = [
  { id: 'c1', title: 'Risk engine rollout — go / no-go', project: 'Risk Engine',
    date: 'Today', time: '1:31 PM', dur: '24m 18s', kind: 'notes' },
  { id: 'c2', title: 'Weekly sync with Adeo', project: 'Adeo',
    date: 'Today', time: '12:46 PM', dur: '12m 04s', kind: 'notes', active: true },
  { id: 'c3', title: 'Vendor security review', project: 'Risk Engine',
    date: 'Today', time: '12:44 PM', dur: '8m 47s', kind: 'notes' },
  { id: 'c4', title: 'Standup — blockers & owners', project: null,
    date: 'Yesterday', time: '4:45 PM', dur: '5m 12s', kind: 'transcript' },
  { id: 'c5', title: 'Onboarding flow crit', project: 'Adeo',
    date: 'Yesterday', time: '4:22 PM', dur: '31m 56s', kind: 'notes' },
  { id: 'c6', title: '1:1 with Priya', project: null,
    date: 'Mon', time: '9:05 AM', dur: '18m 30s', kind: 'notes' },
];

const NOTE = {
  title: 'Weekly sync with Adeo',
  date: 'Jun 10, 2026', time: '12:46 PM', project: 'Adeo', dur: '12m 04s',
  model: 'llama3.2',
  summary: 'A check-in on the ongoing project and where it goes next. No major decisions were taken, but the team aligned on near-term milestones and who owns the planning doc.',
  points: ['Project progress against the current plan', 'Team roles and responsibilities', 'Upcoming milestones and sequencing'],
  decisions: ['None were made during this meeting.'],
  actions: ['Follow up with the team lead on the project planning document by end of week.'],
  questions: ['What is the current status of the project plan?'],
};

// ============================================================ brand bits
function Bird({ size = 40, style = {} }) {
  return <img src="assets/logo_256.png" alt="" width={size} height={size}
    style={{ display: 'block', objectFit: 'contain', ...style }} />;
}

function Wordmark({ size = 30, color }) {
  const a = color || P.ink, b = color ? color : '#6B5E3A';
  return (
    <span style={{ fontFamily: DISP, fontWeight: 800, fontSize: size,
      letterSpacing: -0.5, lineHeight: 1, display: 'inline-flex' }}>
      <span style={{ color: a }}>Yap</span>
      <span style={{ color: b }}>Yap</span>
      <span style={{ color: a }}>Yap</span>
    </span>
  );
}

function WinControls({ dark = false }) {
  const c = dark ? P.ink : P.inkSoft;
  const btn = { width: 44, height: 30, display: 'flex', alignItems: 'center',
    justifyContent: 'center', cursor: 'default' };
  return (
    <div style={{ display: 'flex', WebkitAppRegion: 'no-drag' }}>
      <div style={btn}><svg width="11" height="11" viewBox="0 0 11 11"><line x1="1" y1="6" x2="10" y2="6" stroke={c} strokeWidth="1.1"/></svg></div>
      <div style={btn}><svg width="10" height="10" viewBox="0 0 10 10"><rect x="1" y="1" width="8" height="8" fill="none" stroke={c} strokeWidth="1.1"/></svg></div>
      <div style={{ ...btn, borderRadius: 0 }} className="yyy-close"><svg width="11" height="11" viewBox="0 0 11 11"><line x1="1" y1="1" x2="10" y2="10" stroke={c} strokeWidth="1.1"/><line x1="10" y1="1" x2="1" y2="10" stroke={c} strokeWidth="1.1"/></svg></div>
    </div>
  );
}

// ============================================================ icons
const ic = (path, o = {}) => (
  <svg width={o.s || 16} height={o.s || 16} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth={o.w || 1.7} strokeLinecap="round"
    strokeLinejoin="round" style={o.style}>{path}</svg>
);
const Gear = (o) => ic(<><circle cx="12" cy="12" r="3.2"/><path d="M12 2.5v2M12 19.5v2M21.5 12h-2M4.5 12h-2M18.7 5.3l-1.4 1.4M6.7 17.3l-1.4 1.4M18.7 18.7l-1.4-1.4M6.7 6.7L5.3 5.3"/></>, o);
const Sparkle = (o) => ic(<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>, o);
const Search = (o) => ic(<><circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/></>, o);
const Kebab = (o) => ic(<><circle cx="12" cy="5" r="1.2" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="12" cy="19" r="1.2" fill="currentColor" stroke="none"/></>, o);
const ChevDown = (o) => ic(<path d="M5 9l7 7 7-7"/>, { ...o, w: o?.w || 2 });
const ChevRight = (o) => ic(<path d="M9 5l7 7-7 7"/>, { ...o, w: o?.w || 2 });
const Mic = (o) => ic(<><rect x="9" y="2.5" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/></>, o);
const Plus = (o) => ic(<path d="M12 5v14M5 12h14"/>, { ...o, w: o?.w || 2 });
const Lock = (o) => ic(<><rect x="4.5" y="10.5" width="15" height="10" rx="2.2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/></>, o);
const Home = (o) => ic(<path d="M4 11l8-7 8 7M6 9.5V20h12V9.5"/>, o);
const Folder = (o) => ic(<path d="M3.5 6.5h5l2 2.5h10v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 2.5 18V8a1.5 1.5 0 0 1 1.5-1.5z"/>, o);
const Copy = (o) => ic(<><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/></>, o);
const Export = (o) => ic(<><path d="M12 15V3M8 7l4-4 4 4"/><path d="M5 13v6a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6"/></>, o);
const Dots = (o) => ic(<><circle cx="6" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.3" fill="currentColor" stroke="none"/><circle cx="18" cy="12" r="1.3" fill="currentColor" stroke="none"/></>, o);

// ============================================================ small ui
function StatusChip({ label = 'Ready', dot = P.subtle, fg = P.muted, bg = P.surface }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8,
      background: bg, border: `1px solid ${P.border}`, borderRadius: 999,
      padding: '7px 14px 7px 12px', fontFamily: UI, fontSize: 13,
      fontWeight: 500, color: fg }}>
      <span style={{ width: 8, height: 8, borderRadius: 999, background: dot }} />
      {label}
    </span>
  );
}

function ProjectPill({ name = 'No project', onLight = false }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8,
      background: onLight ? P.surface : 'rgba(255,255,255,0.55)',
      border: `1px solid ${P.border}`, borderRadius: 999, padding: '8px 12px 8px 14px',
      fontFamily: UI, fontSize: 13.5, fontWeight: 500, color: P.inkSoft }}>
      <span style={{ width: 8, height: 8, borderRadius: 2,
        background: name === 'No project' ? P.subtle : P.amber }} />
      {name}
      <span style={{ color: P.subtle, display: 'inline-flex' }}><ChevDown s={14} /></span>
    </span>
  );
}

function ProjectTag({ name }) {
  if (!name) return (
    <span style={{ fontFamily: UI, fontSize: 11.5, color: P.subtle, fontWeight: 500 }}>No project</span>
  );
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5,
      fontFamily: UI, fontSize: 11.5, fontWeight: 600, color: P.amber, whiteSpace: 'nowrap' }}>
      <span style={{ width: 6, height: 6, borderRadius: 2, background: P.amber }} />
      {name}
    </span>
  );
}

// A single conversation row
function ConvCard({ item, compact = false }) {
  const on = item.active;
  return (
    <div style={{ position: 'relative', borderRadius: 12,
      background: on ? P.soft : 'transparent',
      border: `1px solid ${on ? P.yellowDeep : 'transparent'}`,
      padding: compact ? '10px 12px' : '12px 14px', cursor: 'default',
      transition: 'background .12s' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontFamily: UI, fontSize: compact ? 13.5 : 14.5,
            fontWeight: 600, color: P.ink, lineHeight: 1.3, marginBottom: 5,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.title}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7,
            fontFamily: UI, fontSize: 11.5, color: P.muted, fontWeight: 500, whiteSpace: 'nowrap' }}>
            <span>{item.date} · {item.time}</span>
            <span style={{ color: P.border }}>•</span>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{item.dur}</span>
          </div>
          <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
            <ProjectTag name={item.project} />
            {item.kind === 'transcript' && (
              <span style={{ fontFamily: UI, fontSize: 10.5, fontWeight: 600,
                color: P.subtle, letterSpacing: 0.3 }}>TRANSCRIPT ONLY</span>
            )}
          </div>
        </div>
        <span style={{ color: on ? P.muted : P.subtle, marginTop: 2, opacity: on ? 1 : 0.5 }}><Kebab s={15} /></span>
      </div>
    </div>
  );
}

function ConvList({ items = CONVERSATIONS, compact = false }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: compact ? 2 : 3 }}>
      {items.map((it) => <ConvCard key={it.id} item={it} compact={compact} />)}
    </div>
  );
}

// Section label inside the reader
function SecLabel({ children, color = P.muted }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
      <span style={{ width: 7, height: 7, borderRadius: 2, background: P.yellow, boxShadow: `0 0 0 1px ${P.yellowDeep}` }} />
      <span style={{ fontFamily: UI, fontSize: 11.5, fontWeight: 700, letterSpacing: 0.9,
        textTransform: 'uppercase', color, whiteSpace: 'nowrap' }}>{children}</span>
    </div>
  );
}

function Bullet({ children }) {
  return (
    <li style={{ display: 'flex', gap: 11, alignItems: 'flex-start', marginBottom: 9 }}>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: P.amber, marginTop: 8, flex: '0 0 auto' }} />
      <span style={{ fontFamily: UI, fontSize: 14.5, lineHeight: 1.55, color: P.inkSoft }}>{children}</span>
    </li>
  );
}

function ActionItem({ children }) {
  return (
    <li style={{ display: 'flex', gap: 11, alignItems: 'flex-start', marginBottom: 10 }}>
      <span style={{ width: 16, height: 16, borderRadius: 5, border: `1.6px solid ${P.borderDeep}`,
        background: P.white, marginTop: 2, flex: '0 0 auto' }} />
      <span style={{ fontFamily: UI, fontSize: 14.5, lineHeight: 1.55, color: P.inkSoft }}>{children}</span>
    </li>
  );
}

// The notes document body, reused by every direction
function NotesReader({ pad = '28px 34px', showHeader = true, maxWidth = null }) {
  const n = NOTE;
  return (
    <div style={{ padding: pad, maxWidth: maxWidth || 'none', margin: maxWidth ? '0 auto' : 0 }}>
      {showHeader && (
        <div style={{ marginBottom: 22 }}>
          <h1 style={{ margin: 0, fontFamily: DISP, fontWeight: 700, fontSize: 27,
            letterSpacing: -0.5, color: P.ink, lineHeight: 1.15 }}>{n.title}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginTop: 10,
            fontFamily: UI, fontSize: 12.5, color: P.muted, fontWeight: 500 }}>
            <span>{n.date} · {n.time}</span>
            <span style={{ color: P.border }}>•</span>
            <ProjectTag name={n.project} />
            <span style={{ color: P.border }}>•</span>
            <span style={{ fontVariantNumeric: 'tabular-nums' }}>{n.dur}</span>
          </div>
        </div>
      )}

      <div style={{ marginBottom: 24 }}>
        <SecLabel>Summary</SecLabel>
        <p style={{ margin: 0, fontFamily: UI, fontSize: 15.5, lineHeight: 1.62, color: P.inkSoft }}>{n.summary}</p>
      </div>

      <div style={{ marginBottom: 24 }}>
        <SecLabel>Key discussion points</SecLabel>
        <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {n.points.map((p, i) => <Bullet key={i}>{p}</Bullet>)}
        </ul>
      </div>

      <div style={{ marginBottom: 24 }}>
        <SecLabel>Decisions</SecLabel>
        <p style={{ margin: 0, fontFamily: UI, fontSize: 14.5, lineHeight: 1.55, color: P.muted, fontStyle: 'italic' }}>{n.decisions[0]}</p>
      </div>

      <div style={{ marginBottom: 24 }}>
        <SecLabel>Action items</SecLabel>
        <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {n.actions.map((p, i) => <ActionItem key={i}>{p}</ActionItem>)}
        </ul>
      </div>

      <div>
        <SecLabel>Open questions</SecLabel>
        <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
          {n.questions.map((p, i) => <Bullet key={i}>{p}</Bullet>)}
        </ul>
      </div>
    </div>
  );
}

// Notes / Transcript pill toggle
function ReaderTabs({ active = 'notes' }) {
  const tab = (id, label) => {
    const on = id === active;
    return (
      <span style={{ padding: '6px 14px', borderRadius: 999, fontFamily: UI,
        fontSize: 13, fontWeight: 600, color: on ? P.ink : P.muted,
        background: on ? P.white : 'transparent',
        boxShadow: on ? '0 1px 2px rgba(0,0,0,0.08)' : 'none' }}>{label}</span>
    );
  };
  return (
    <div style={{ display: 'inline-flex', gap: 2, padding: 3, borderRadius: 999,
      background: P.card, border: `1px solid ${P.border}` }}>
      {tab('notes', 'Notes')}{tab('transcript', 'Transcript')}
    </div>
  );
}

// A caption shown under each window on the canvas
function Caption({ tag, title, body }) {
  return (
    <div style={{ padding: '14px 4px 0', fontFamily: UI, maxWidth: 760 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 4 }}>
        <span style={{ fontFamily: DISP, fontWeight: 700, fontSize: 15, color: '#2a251f' }}>{tag}</span>
        <span style={{ fontSize: 14.5, fontWeight: 600, color: 'rgba(40,30,20,0.78)' }}>{title}</span>
      </div>
      <div style={{ fontSize: 13, lineHeight: 1.5, color: 'rgba(60,50,40,0.62)' }}>{body}</div>
    </div>
  );
}

Object.assign(window, {
  P, DISP, UI, CONVERSATIONS, NOTE,
  Bird, Wordmark, WinControls,
  Gear, Sparkle, Search, Kebab, ChevDown, ChevRight, Mic, Plus, Lock, Home, Folder, Copy, Export, Dots,
  StatusChip, ProjectPill, ProjectTag, ConvCard, ConvList,
  SecLabel, Bullet, ActionItem, NotesReader, ReaderTabs, Caption,
});
