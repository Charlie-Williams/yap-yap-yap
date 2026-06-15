// shell.jsx — the Direction B "workspace rail" shell, generalized so every
// main-window state (idle / recording / processing / generating / transcript /
// empty) shares the exact same chrome. Exports RailShell + small bits.

const { P, DISP, UI, Bird, Wordmark, WinControls, Gear, Search, Mic, Plus, Lock,
  Home, Folder, Copy, Export, Kebab, ChevDown, ChevRight, ConvList, ReaderTabs,
  ProjectTag, CONVERSATIONS } = window;

const SH_WIN = '0 30px 80px -24px rgba(45,33,8,0.45), 0 10px 30px rgba(45,33,8,0.14)';

function Win({ children, bg = P.bg }) {
  return (
    <div style={{ width: 1080, height: 720, borderRadius: 16, overflow: 'hidden',
      position: 'relative', background: bg, boxShadow: SH_WIN,
      border: '1px solid rgba(120,90,20,0.18)' }}>{children}</div>
  );
}

function SearchField({ placeholder = 'Search conversations', light = true }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 9, height: 38,
      padding: '0 14px', borderRadius: 10, background: light ? P.white : P.surface,
      border: `1px solid ${P.border}` }}>
      <span style={{ color: P.subtle, display: 'inline-flex' }}><Search s={16} /></span>
      <span style={{ fontFamily: UI, fontSize: 13.5, color: P.subtle, fontWeight: 500 }}>{placeholder}</span>
    </div>
  );
}

function IconBtn({ children, light = false }) {
  return (
    <span style={{ width: 34, height: 34, borderRadius: 9, display: 'inline-flex',
      alignItems: 'center', justifyContent: 'center', color: P.muted,
      background: light ? P.white : 'transparent', border: `1px solid ${P.border}` }}>
      {children}
    </span>
  );
}

function NavItem({ icon, label, active, sub }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 12px',
      borderRadius: 10, marginBottom: 2,
      background: active ? 'rgba(255,255,255,0.55)' : 'transparent',
      border: `1px solid ${active ? 'rgba(120,90,20,0.16)' : 'transparent'}`,
      color: active ? P.ink : P.inkSoft }}>
      <span style={{ display: 'inline-flex', color: active ? P.ink : '#6B5E3A' }}>{icon}</span>
      <span style={{ fontFamily: UI, fontSize: 14, fontWeight: active ? 700 : 600, flex: 1, whiteSpace: 'nowrap' }}>{label}</span>
      {sub}
    </div>
  );
}

// The record control in the rail, varying by state.
function RailRecord({ state = 'idle', timer = '00:00' }) {
  if (state === 'recording') {
    return (
      <div style={{ marginBottom: 14 }}>
        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          width: '100%', boxSizing: 'border-box', padding: '13px 18px', borderRadius: 12,
          background: P.record, border: `1px solid ${P.record}`,
          boxShadow: '0 2px 0 rgba(140,20,20,0.35), 0 6px 16px rgba(229,72,77,0.35)',
          fontFamily: UI, fontWeight: 700, fontSize: 15, color: P.white, whiteSpace: 'nowrap' }}>
          <span style={{ width: 11, height: 11, borderRadius: 2, background: P.white }} />
          Stop recording
        </span>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 10 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: P.record }} />
          <span style={{ fontFamily: UI, fontSize: 13, fontWeight: 700, color: P.inkSoft, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', flexShrink: 0 }}>{`Recording · ${timer}`.replace(/ /g, '\u00A0')}</span>
        </div>
      </div>
    );
  }
  if (state === 'processing') {
    return (
      <div style={{ marginBottom: 14 }}>
        <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          width: '100%', boxSizing: 'border-box', padding: '13px 18px', borderRadius: 12,
          background: 'rgba(26,26,23,0.35)', border: '1px solid rgba(26,26,23,0.15)',
          fontFamily: UI, fontWeight: 700, fontSize: 15, color: 'rgba(26,26,23,0.5)', whiteSpace: 'nowrap' }}>
          <span style={{ width: 9, height: 9, borderRadius: 999, background: 'rgba(229,72,77,0.5)' }} />
          Start recording
        </span>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 10 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: P.amber }} />
          <span style={{ fontFamily: UI, fontSize: 13, fontWeight: 700, color: P.amber, whiteSpace: 'nowrap', flexShrink: 0 }}>{'Transcribing… 47%'.replace(/ /g, '\u00A0')}</span>
        </div>
      </div>
    );
  }
  // idle
  return (
    <div style={{ marginBottom: 14 }}>
      <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
        width: '100%', boxSizing: 'border-box', padding: '13px 18px', borderRadius: 12,
        background: P.ink, border: `1px solid ${P.ink}`,
        boxShadow: '0 2px 0 rgba(0,0,0,0.25), 0 6px 16px rgba(0,0,0,0.22)',
        fontFamily: UI, fontWeight: 700, fontSize: 15, color: P.white, whiteSpace: 'nowrap' }}>
        <span style={{ width: 9, height: 9, borderRadius: 999, background: P.record }} />
        Start recording
      </span>
    </div>
  );
}

function Rail({ state = 'idle', timer = '00:00', nav = 'all' }) {
  return (
    <div style={{ width: 252, background: P.yellow, borderRight: `1px solid ${P.yellowDeep}`,
      display: 'flex', flexDirection: 'column', padding: '20px 16px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, paddingLeft: 4 }}>
        <Bird size={34} />
        <Wordmark size={20} />
      </div>
      <RailRecord state={state} timer={timer} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px',
        borderRadius: 10, background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(120,90,20,0.16)',
        marginBottom: 22, fontFamily: UI, fontSize: 13, fontWeight: 600, color: P.inkSoft, whiteSpace: 'nowrap' }}>
        <span style={{ width: 8, height: 8, borderRadius: 2, background: P.subtle }} />
        No project
        <div style={{ flex: 1 }} />
        <ChevDown s={14} />
      </div>

      <NavItem icon={<Home s={18} />} label="All conversations" active={nav === 'all'} />
      <NavItem icon={<Folder s={18} />} label="Projects" sub={<ChevDown s={14} style={{ opacity: 0.6 }} />} />
      <div style={{ paddingLeft: 18, marginBottom: 2 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', fontFamily: UI, fontSize: 13, fontWeight: 600, color: '#6B5E3A', whiteSpace: 'nowrap' }}>
          <span style={{ width: 6, height: 6, borderRadius: 2, background: P.amber }} />Adeo</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', fontFamily: UI, fontSize: 13, fontWeight: 600, color: '#6B5E3A', whiteSpace: 'nowrap' }}>
          <span style={{ width: 6, height: 6, borderRadius: 2, background: P.amber }} />Risk Engine</div>
      </div>
      <NavItem icon={<Gear s={18} />} label="Settings" active={nav === 'settings'} />

      <div style={{ flex: 1 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '11px 12px',
        borderRadius: 10, background: 'rgba(255,255,255,0.35)', border: '1px solid rgba(120,90,20,0.14)' }}>
        <span style={{ color: P.inkSoft, display: 'inline-flex' }}><Lock s={16} /></span>
        <span style={{ fontFamily: UI, fontSize: 11.5, fontWeight: 600, color: P.inkSoft, lineHeight: 1.35 }}>
          Everything stays<br />on this PC</span>
      </div>
    </div>
  );
}

function ListColumn({ items = CONVERSATIONS, compact = true, topItem = null, empty = false }) {
  return (
    <div style={{ width: 304, background: P.surface, borderRight: `1px solid ${P.border}`,
      display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '20px 16px 12px' }}>
        <div style={{ fontFamily: DISP, fontWeight: 700, fontSize: 18, color: P.ink, marginBottom: 12 }}>All conversations</div>
        <SearchField />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }}>
          <span style={{ fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.subtle, whiteSpace: 'nowrap' }}>{empty ? 'No conversations yet' : `${items.length} conversations`}</span>
          {!empty && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.muted }}>Newest <ChevDown s={13} /></span>}
        </div>
      </div>
      <div style={{ flex: 1, padding: '0 8px', overflow: 'hidden' }}>
        {empty ? (
          <div style={{ padding: '28px 14px', textAlign: 'center' }}>
            <div style={{ fontFamily: UI, fontSize: 13, color: P.subtle, lineHeight: 1.5 }}>
              Conversations you record will appear here, newest first.
            </div>
          </div>
        ) : (
          <React.Fragment>
            {topItem}
            <ConvList items={items} compact={compact} />
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

// Reader pane with an optional top bar (tabs + actions + window controls).
function ReaderPane({ tabs = 'notes', actions = true, children, bg = P.paper }) {
  return (
    <div style={{ flex: 1, background: bg, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
      <div style={{ height: 56, borderBottom: `1px solid ${P.border}`, display: 'flex',
        alignItems: 'center', justifyContent: 'space-between', padding: '0 0 0 24px', flex: '0 0 auto' }}>
        {tabs ? <ReaderTabs active={tabs} /> : <div />}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 6 }}>
          {actions && <React.Fragment>
            <IconBtn light><Copy s={16} /></IconBtn>
            <IconBtn light><Export s={16} /></IconBtn>
            <div style={{ width: 1, height: 24, background: P.border, margin: '0 4px' }} />
          </React.Fragment>}
          <WinControls />
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>{children}</div>
    </div>
  );
}

// Full shell composing rail + list + reader.
function RailShell({ state = 'idle', timer = '00:00', items, topItem, emptyList = false,
  tabs = 'notes', actions = true, reader, readerBg }) {
  return (
    <Win>
      <div style={{ display: 'flex', height: '100%' }}>
        <Rail state={state} timer={timer} />
        <ListColumn items={items} topItem={topItem} empty={emptyList} />
        <ReaderPane tabs={tabs} actions={actions} bg={readerBg}>{reader}</ReaderPane>
      </div>
    </Win>
  );
}

Object.assign(window, { Win, SearchField, IconBtn, NavItem, Rail, RailRecord, ListColumn, ReaderPane, RailShell });
