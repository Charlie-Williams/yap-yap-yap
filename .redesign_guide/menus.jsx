// menus.jsx — context menus shown as detail crops: the conversation "⋯" menu
// (with the Assign-to-project flyout) and the rail project picker.

const { P, DISP, UI, Kebab, ChevRight, Plus, ConvCard, Folder } = window;

const MENU_SHADOW = '0 12px 36px rgba(45,33,8,0.22), 0 0 0 1px rgba(45,33,8,0.06)';

function MItem({ children, danger = false, chevron = false, hover = false, dot = false }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 11px', borderRadius: 7,
      background: hover ? (danger ? 'rgba(229,72,77,0.1)' : 'rgba(26,26,23,0.05)') : 'transparent',
      fontFamily: UI, fontSize: 13.5, fontWeight: 500, color: danger ? P.record : P.inkSoft }}>
      {dot !== false && <span style={{ width: 7, height: 7, borderRadius: 999, background: dot === true ? P.ink : 'transparent', flex: '0 0 auto' }} />}
      <span style={{ flex: 1 }}>{children}</span>
      {chevron && <ChevRight s={14} style={{ opacity: 0.5 }} />}
    </div>
  );
}

function Sep() { return <div style={{ height: 1, background: 'rgba(45,33,8,0.08)', margin: '5px 4px' }} />; }

function Menu({ children, w = 210 }) {
  return (
    <div style={{ width: w, background: P.white, borderRadius: 11, boxShadow: MENU_SHADOW, padding: 5 }}>{children}</div>
  );
}

// conversation ⋯ menu, with the Assign-to-project flyout open
function ConvMenuDetail() {
  return (
    <div style={{ width: 560, height: 360, position: 'relative', display: 'flex' }}>
      {/* context: a conversation card */}
      <div style={{ width: 300, background: P.surface, border: `1px solid ${P.border}`, borderRadius: 14,
        padding: 8, height: 'fit-content', boxShadow: '0 10px 30px -16px rgba(60,45,10,0.3)' }}>
        <ConvCard item={{ id: 'x', title: 'Weekly sync with Adeo', project: 'Adeo', date: 'Today', time: '12:46 PM', dur: '12m 04s', kind: 'notes', active: true }} compact />
      </div>
      {/* primary menu */}
      <div style={{ position: 'absolute', left: 250, top: 24 }}>
        <Menu>
          <MItem chevron hover>Assign to project</MItem>
          <Sep />
          <MItem>Hide from list</MItem>
          <MItem danger>Delete from computer</MItem>
        </Menu>
      </div>
      {/* flyout submenu */}
      <div style={{ position: 'absolute', left: 462, top: 18 }}>
        <Menu w={170}>
          <MItem dot={true}>No project</MItem>
          <MItem dot={false}>Adeo</MItem>
          <MItem dot={false}>Risk Engine</MItem>
        </Menu>
      </div>
    </div>
  );
}

// rail project picker, open
function ProjectMenuDetail() {
  return (
    <div style={{ width: 320, height: 280, position: 'relative' }}>
      {/* the pill */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px', width: 220,
        borderRadius: 10, background: P.yellow, border: '1px solid rgba(120,90,20,0.2)',
        fontFamily: UI, fontSize: 13, fontWeight: 600, color: P.inkSoft }}>
        <span style={{ width: 8, height: 8, borderRadius: 2, background: P.subtle }} />
        No project
        <div style={{ flex: 1 }} />
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 9l7 7 7-7"/></svg>
      </div>
      <div style={{ position: 'absolute', top: 48, left: 0 }}>
        <Menu w={220}>
          <MItem dot={true}>No project</MItem>
          <MItem dot={false}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 7, height: 7, borderRadius: 2, background: P.amber }} />Adeo</span></MItem>
          <MItem dot={false}><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><span style={{ width: 7, height: 7, borderRadius: 2, background: P.amber }} />Risk Engine</span></MItem>
          <Sep />
          <MItem><span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: P.muted }}><Plus s={14} />Manage projects…</span></MItem>
        </Menu>
      </div>
    </div>
  );
}

Object.assign(window, { ConvMenuDetail, ProjectMenuDetail });
