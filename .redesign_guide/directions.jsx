// directions.jsx — three layout directions for the YapYapYap main page.
// Each component renders a 1080×720 desktop window + a caption beneath it.

const { P, DISP, UI, Bird, Wordmark, WinControls, Gear, Sparkle, Search, Kebab,
  ChevDown, ChevRight, Mic, Plus, Lock, Home, Folder, Copy, Export, Dots,
  StatusChip, ProjectPill, ProjectTag, ConvList, NotesReader, ReaderTabs,
  Caption } = window;

const WIN_SHADOW = '0 30px 80px -24px rgba(45,33,8,0.45), 0 10px 30px rgba(45,33,8,0.14)';

function Window({ children, bg = P.bg }) {
  return (
    <div style={{ width: 1080, height: 720, borderRadius: 16, overflow: 'hidden',
      position: 'relative', background: bg, boxShadow: WIN_SHADOW,
      border: '1px solid rgba(120,90,20,0.18)' }}>
      {children}
    </div>
  );
}

function Frame({ children, caption }) {
  return (
    <div>
      <Window>{children}</Window>
      {caption}
    </div>
  );
}

function SettingsPill({ onYellow = true }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7,
      padding: '8px 14px', borderRadius: 999, fontFamily: UI, fontSize: 13.5,
      fontWeight: 600, color: P.inkSoft,
      background: onYellow ? 'rgba(255,255,255,0.45)' : P.surface,
      border: `1px solid ${onYellow ? 'rgba(120,90,20,0.18)' : P.border}` }}>
      <span style={{ display: 'inline-flex' }}><Gear s={15} /></span>Settings
    </span>
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

function RecBtn({ variant = 'yellow', label = 'Start recording', full = false }) {
  const yellow = variant === 'yellow';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      gap: 10, padding: '13px 22px', borderRadius: 12,
      width: full ? '100%' : 'auto', boxSizing: 'border-box',
      background: yellow ? P.yellow : P.ink,
      border: `1px solid ${yellow ? P.yellowDeep : P.ink}`,
      boxShadow: yellow ? '0 2px 0 rgba(180,140,10,0.35), 0 6px 16px rgba(200,160,20,0.28)'
        : '0 2px 0 rgba(0,0,0,0.25), 0 6px 16px rgba(0,0,0,0.22)',
      fontFamily: UI, fontWeight: 700, fontSize: 15,
      color: yellow ? P.ink : P.white }}>
      <span style={{ width: 9, height: 9, borderRadius: 999, background: P.record,
        boxShadow: `0 0 0 3px ${yellow ? 'rgba(229,72,77,0.2)' : 'rgba(229,72,77,0.3)'}` }} />
      {label}
    </span>
  );
}

function IconBtn({ children, light = true }) {
  return (
    <span style={{ width: 34, height: 34, borderRadius: 9, display: 'inline-flex',
      alignItems: 'center', justifyContent: 'center', color: P.muted,
      background: light ? P.white : 'transparent', border: `1px solid ${P.border}` }}>
      {children}
    </span>
  );
}

function Panel({ children, style = {} }) {
  return (
    <div style={{ background: P.surface, border: `1px solid ${P.border}`,
      borderRadius: 16, boxShadow: '0 1px 2px rgba(60,45,10,0.05), 0 12px 28px -16px rgba(60,45,10,0.22)',
      overflow: 'hidden', ...style }}>{children}</div>
  );
}

// ════════════════════════════════════════════════ A · Classic header
function DirectionA() {
  return (
    <Frame caption={<Caption tag="A" title="Refined classic"
      body="The current shape, polished. A bold yellow header, a focused record toolbar, and a calm two-pane reading layout — familiar, premium, low-risk." />}>
      {/* header */}
      <div style={{ position: 'relative', background: P.yellow, height: 104,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 26px', borderBottom: `1px solid ${P.yellowDeep}` }}>
        <div style={{ position: 'absolute', top: 0, right: 0 }}><WinControls dark /></div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
          <Bird size={48} />
          <Wordmark size={30} />
        </div>
        <SettingsPill />
      </div>

      {/* record toolbar */}
      <div style={{ padding: '18px 24px' }}>
        <Panel style={{ borderRadius: 16, padding: '13px 14px', display: 'flex',
          alignItems: 'center', gap: 13, boxShadow: 'none' }}>
          <RecBtn />
          <ProjectPill name="No project" onLight />
          <StatusChip />
          <div style={{ flex: 1 }} />
          <div style={{ width: 240 }}><SearchField /></div>
        </Panel>
      </div>

      {/* body */}
      <div style={{ display: 'flex', gap: 18, padding: '0 24px 24px', height: 470 }}>
        <Panel style={{ width: 314, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '15px 16px 10px', display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span style={{ fontFamily: DISP, fontWeight: 700, fontSize: 15.5, color: P.ink }}>Conversations</span>
            <span style={{ fontFamily: UI, fontSize: 12.5, color: P.subtle, fontWeight: 600 }}>6</span>
          </div>
          <div style={{ padding: '0 8px 10px' }}><ConvList /></div>
        </Panel>

        <Panel style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '13px 20px', borderBottom: `1px solid ${P.border}`,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <ReaderTabs active="notes" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <IconBtn><Copy s={16} /></IconBtn>
              <IconBtn><Export s={16} /></IconBtn>
              <IconBtn><Kebab s={16} /></IconBtn>
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden', background: P.paper }}>
            <NotesReader pad="26px 32px" />
          </div>
        </Panel>
      </div>
    </Frame>
  );
}

// ════════════════════════════════════════════════ B · Workspace rail
function NavItem({ icon, label, active, sub }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '9px 12px',
      borderRadius: 10, marginBottom: 2,
      background: active ? 'rgba(255,255,255,0.55)' : 'transparent',
      border: `1px solid ${active ? 'rgba(120,90,20,0.16)' : 'transparent'}`,
      color: active ? P.ink : P.inkSoft }}>
      <span style={{ display: 'inline-flex', color: active ? P.ink : '#6B5E3A' }}>{icon}</span>
      <span style={{ fontFamily: UI, fontSize: 14, fontWeight: active ? 700 : 600, flex: 1 }}>{label}</span>
      {sub}
    </div>
  );
}

function DirectionB() {
  return (
    <Frame caption={<Caption tag="B" title="Workspace rail"
      body="A persistent yellow rail puts the record button and projects one click away, a dedicated list column, and a clean white reading surface. Scales best as the library grows." />}>
      <div style={{ display: 'flex', height: '100%' }}>
        {/* rail */}
        <div style={{ width: 252, background: P.yellow, borderRight: `1px solid ${P.yellowDeep}`,
          display: 'flex', flexDirection: 'column', padding: '20px 16px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, paddingLeft: 4 }}>
            <Bird size={34} />
            <Wordmark size={20} />
          </div>
          <div style={{ marginBottom: 8 }}><RecBtn variant="ink" full /></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px',
            borderRadius: 10, background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(120,90,20,0.16)',
            marginBottom: 22, fontFamily: UI, fontSize: 13, fontWeight: 600, color: P.inkSoft }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: P.subtle }} />
            No project
            <div style={{ flex: 1 }} />
            <ChevDown s={14} />
          </div>

          <NavItem icon={<Home s={18} />} label="All conversations" active />
          <NavItem icon={<Folder s={18} />} label="Projects" sub={<ChevDown s={14} style={{ opacity: 0.6 }} />} />
          <div style={{ paddingLeft: 18, marginBottom: 2 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', fontFamily: UI, fontSize: 13, fontWeight: 600, color: '#6B5E3A' }}>
              <span style={{ width: 6, height: 6, borderRadius: 2, background: P.amber }} />Adeo</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', fontFamily: UI, fontSize: 13, fontWeight: 600, color: '#6B5E3A' }}>
              <span style={{ width: 6, height: 6, borderRadius: 2, background: P.amber }} />Risk Engine</div>
          </div>
          <NavItem icon={<Gear s={18} />} label="Settings" />

          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '11px 12px',
            borderRadius: 10, background: 'rgba(255,255,255,0.35)', border: '1px solid rgba(120,90,20,0.14)' }}>
            <span style={{ color: P.inkSoft, display: 'inline-flex' }}><Lock s={16} /></span>
            <span style={{ fontFamily: UI, fontSize: 11.5, fontWeight: 600, color: P.inkSoft, lineHeight: 1.35 }}>
              Everything stays<br />on this PC</span>
          </div>
        </div>

        {/* list column */}
        <div style={{ width: 304, background: P.surface, borderRight: `1px solid ${P.border}`,
          display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '20px 16px 12px' }}>
            <div style={{ fontFamily: DISP, fontWeight: 700, fontSize: 18, color: P.ink, marginBottom: 12 }}>All conversations</div>
            <SearchField />
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }}>
              <span style={{ fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.subtle }}>6 conversations</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.muted }}>Newest <ChevDown s={13} /></span>
            </div>
          </div>
          <div style={{ flex: 1, padding: '0 8px', overflow: 'hidden' }}><ConvList compact /></div>
        </div>

        {/* reader */}
        <div style={{ flex: 1, background: P.paper, display: 'flex', flexDirection: 'column' }}>
          <div style={{ height: 56, borderBottom: `1px solid ${P.border}`, display: 'flex',
            alignItems: 'center', justifyContent: 'space-between', padding: '0 0 0 24px' }}>
            <ReaderTabs active="notes" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingRight: 6 }}>
              <IconBtn light={false}><Copy s={16} /></IconBtn>
              <IconBtn light={false}><Export s={16} /></IconBtn>
              <div style={{ width: 1, height: 24, background: P.border, margin: '0 4px' }} />
              <WinControls />
            </div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <NotesReader pad="34px 44px" maxWidth={620} />
          </div>
        </div>
      </div>
    </Frame>
  );
}

// ════════════════════════════════════════════════ C · Focus document
function DirectionC() {
  return (
    <Frame caption={<Caption tag="C" title="Focus document"
      body="The notes become the hero — a floating page on the yellow canvas — with a slim list at the side and one friendly, always-there record button. The lightest, most premium feel." />}>
      {/* slim titlebar */}
      <div style={{ height: 44, background: P.yellow, borderBottom: `1px solid ${P.yellowDeep}`,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 0 0 18px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <Bird size={22} />
          <Wordmark size={16} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <SettingsPill />
          <WinControls dark />
        </div>
      </div>

      <div style={{ display: 'flex', height: 676 }}>
        {/* list rail */}
        <div style={{ width: 272, background: P.surface, borderRight: `1px solid ${P.border}`,
          display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '18px 14px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 12 }}>
              <span style={{ fontFamily: DISP, fontWeight: 700, fontSize: 15.5, color: P.ink }}>Conversations</span>
              <span style={{ fontFamily: UI, fontSize: 12, color: P.subtle, fontWeight: 600 }}>6</span>
            </div>
            <SearchField placeholder="Search" />
          </div>
          <div style={{ flex: 1, padding: '0 7px', overflow: 'hidden' }}><ConvList compact /></div>
        </div>

        {/* canvas with floating page */}
        <div style={{ flex: 1, background: P.bg, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 20, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 2 }}>
            <ReaderTabs active="notes" />
          </div>
          <div style={{ position: 'absolute', top: 64, left: '50%', transform: 'translateX(-50%)',
            width: 588, background: P.paper, borderRadius: 16, border: `1px solid ${P.border}`,
            boxShadow: '0 1px 2px rgba(60,45,10,0.06), 0 30px 60px -24px rgba(60,45,10,0.35)',
            overflow: 'hidden', height: 640 }}>
            <NotesReader pad="36px 44px" />
          </div>

          {/* floating record */}
          <div style={{ position: 'absolute', bottom: 26, left: '50%', transform: 'translateX(-50%)', zIndex: 3 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 11, padding: '13px 14px 13px 13px',
              borderRadius: 999, background: P.yellow, border: `1px solid ${P.yellowDeep}`,
              boxShadow: '0 8px 24px rgba(180,140,10,0.4), 0 2px 0 rgba(180,140,10,0.4)',
              fontFamily: UI, fontWeight: 700, fontSize: 15, color: P.ink }}>
              <Bird size={28} />
              <span style={{ width: 8, height: 8, borderRadius: 999, background: P.record }} />
              Start recording
              <span style={{ paddingRight: 6 }} />
            </span>
          </div>
        </div>
      </div>
    </Frame>
  );
}

Object.assign(window, { DirectionA, DirectionB, DirectionC });
