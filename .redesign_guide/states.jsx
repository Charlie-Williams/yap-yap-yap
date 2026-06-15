// states.jsx — reader bodies + full screen states for the Direction-B platform.

const { P, DISP, UI, Bird, Sparkle, Mic, Lock, Copy, Export, NotesReader,
  SecLabel, RailShell, ConvCard } = window;

// one-time keyframes for live states
if (!document.getElementById('yyy-anim')) {
  const s = document.createElement('style');
  s.id = 'yyy-anim';
  s.textContent = `
  @keyframes yyyPulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.12);opacity:.85}}
  @keyframes yyyBlink{0%,100%{opacity:1}50%{opacity:0}}
  @keyframes yyyShimmer{0%{background-position:-300px 0}100%{background-position:300px 0}}`;
  document.head.appendChild(s);
}

// ---- speaker bars / waveform ----
function Waveform({ heights, color = P.ink, faded = P.border }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, height: 64 }}>
      {heights.map((h, i) => (
        <span key={i} style={{ width: 5, height: `${h}%`, borderRadius: 999,
          background: i % 7 === 3 ? P.amber : (h > 28 ? color : faded) }} />
      ))}
    </div>
  );
}
const WAVE = [18, 34, 52, 70, 44, 26, 60, 82, 48, 30, 64, 90, 56, 38, 22, 46, 72, 88, 54, 32, 20, 40, 66, 80, 50, 28, 58, 76, 42, 24, 16, 36, 62, 84, 52, 30, 68, 86, 46, 26];

// ============================================================ Recording
function RecordingReader() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 26, padding: 40 }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9, padding: '7px 16px',
        borderRadius: 999, background: 'rgba(229,72,77,0.1)', border: `1px solid rgba(229,72,77,0.3)`,
        fontFamily: UI, fontSize: 12.5, fontWeight: 700, letterSpacing: 1, color: P.record }}>
        <span style={{ width: 9, height: 9, borderRadius: 999, background: P.record, animation: 'yyyPulse 1.4s infinite' }} />
        REC
      </span>
      <div style={{ fontFamily: DISP, fontWeight: 700, fontSize: 64, color: P.ink, letterSpacing: -1,
        fontVariantNumeric: 'tabular-nums', lineHeight: 1 }}>00:42</div>
      <div style={{ width: 460 }}><Waveform heights={WAVE} /></div>
      <div style={{ fontFamily: UI, fontSize: 14.5, color: P.muted, fontWeight: 500 }}>
        Listening to your microphone and this PC's audio
      </div>
      <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
        {[['Microphone', P.green], ['System\u00a0audio', P.green]].map(([t, c]) => (
          <span key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 14px',
            borderRadius: 999, background: P.surface, border: `1px solid ${P.border}`, flexShrink: 0,
            fontFamily: UI, fontSize: 12.5, fontWeight: 600, color: P.inkSoft, whiteSpace: 'nowrap' }}>
            <span style={{ width: 7, height: 7, borderRadius: 999, background: c }} />{t}
          </span>
        ))}
      </div>
    </div>
  );
}

// ============================================================ Processing
function Step({ done, label, active }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '4px 0' }}>
      {done ? (
        <span style={{ width: 22, height: 22, borderRadius: 999, background: 'rgba(30,158,87,0.12)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flex: '0 0 auto' }}>
          <svg width="13" height="13" viewBox="0 0 14 14" fill="none" stroke={P.green} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 7.5L5.5 11L12 3.5"/></svg>
        </span>
      ) : (
        <span style={{ width: 22, height: 22, borderRadius: 999, border: `2.5px solid ${P.border}`,
          borderTopColor: P.amber, animation: 'yyyPulse 1.2s infinite', flex: '0 0 auto' }} />
      )}
      <span style={{ fontFamily: UI, fontSize: 15, fontWeight: active ? 700 : 600,
        color: done ? P.muted : (active ? P.ink : P.subtle), whiteSpace: 'nowrap' }}>{label}</span>
      {active && <span style={{ marginLeft: 'auto', fontFamily: UI, fontSize: 13, fontWeight: 700, color: P.amber, fontVariantNumeric: 'tabular-nums' }}>47%</span>}
    </div>
  );
}

function ProcessingReader() {
  const lines = [
    { t: '0:00', s: 'Okay — can everyone hear me? Let me share the rollout doc.' },
    { t: '0:11', s: "Yep, you're coming through. Go ahead." },
    { t: '0:18', s: 'So the risk engine is feature-complete on staging as of this morning.' },
    { t: '0:27', s: 'The open question is whether we flip it on for the whole book or' },
  ];
  return (
    <div style={{ padding: '30px 40px' }}>
      <h1 style={{ margin: '0 0 22px', fontFamily: DISP, fontWeight: 700, fontSize: 23, color: P.ink, letterSpacing: -0.4 }}>Processing your conversation</h1>
      <div style={{ marginBottom: 8 }}>
        <Step done label="Saved the recording" />
        <Step done label="Mixed microphone + system audio" />
        <Step done label="Loaded the Base model" />
        <Step active label="Transcribing the audio" />
      </div>
      <div style={{ height: 6, borderRadius: 999, background: P.card, overflow: 'hidden', margin: '8px 0 26px', maxWidth: 520 }}>
        <div style={{ width: '47%', height: '100%', background: P.amber, borderRadius: 999 }} />
      </div>
      <SecLabel>Transcript so far</SecLabel>
      <div style={{ marginTop: 4 }}>
        {lines.map((l, i) => (
          <div key={i} style={{ display: 'flex', gap: 14, marginBottom: 9 }}>
            <span style={{ fontFamily: UI, fontSize: 12.5, fontWeight: 600, color: P.subtle, fontVariantNumeric: 'tabular-nums', width: 34, flex: '0 0 auto', paddingTop: 1 }}>{l.t}</span>
            <span style={{ fontFamily: UI, fontSize: 14.5, lineHeight: 1.55,
              color: i >= lines.length - 2 ? P.ink : P.muted, fontWeight: i >= lines.length - 2 ? 600 : 500 }}>
              {l.s}{i === lines.length - 1 && <span style={{ display: 'inline-block', width: 2, height: 15, background: P.amber, marginLeft: 3, verticalAlign: 'middle', animation: 'yyyBlink 1s infinite' }} />}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================ Generating notes
function ShimmerLine({ w = '100%' }) {
  return (
    <div style={{ height: 13, width: w, borderRadius: 6, marginBottom: 10,
      background: `linear-gradient(90deg, ${P.card} 0%, #FFF6CF 50%, ${P.card} 100%)`,
      backgroundSize: '600px 100%', animation: 'yyyShimmer 1.4s infinite linear' }} />
  );
}

function GeneratingReader() {
  return (
    <div style={{ padding: '30px 40px', maxWidth: 640 }}>
      <h1 style={{ margin: 0, fontFamily: DISP, fontWeight: 700, fontSize: 26, color: P.ink, letterSpacing: -0.5 }}>Weekly sync with Adeo</h1>
      <div style={{ fontFamily: UI, fontSize: 12.5, color: P.muted, fontWeight: 500, marginTop: 8, marginBottom: 22 }}>Jun 10, 2026 · 12:46 PM · Adeo · 12m 04s</div>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 9, padding: '8px 16px',
        borderRadius: 999, background: 'rgba(184,134,11,0.1)', border: '1px solid rgba(184,134,11,0.25)',
        fontFamily: UI, fontSize: 13, fontWeight: 700, color: P.amber, marginBottom: 26 }}>
        <span style={{ display: 'inline-flex', animation: 'yyyPulse 1.2s infinite' }}><Sparkle s={15} /></span>
        Writing notes…
      </span>
      <div style={{ marginBottom: 24 }}>
        <SecLabel>Summary</SecLabel>
        <p style={{ margin: 0, fontFamily: UI, fontSize: 15.5, lineHeight: 1.62, color: P.inkSoft }}>
          A check-in on the ongoing project and where it goes next. No major decisions were taken, but the team aligned on near-term milestones and who owns the<span style={{ display: 'inline-block', width: 2, height: 16, background: P.amber, marginLeft: 2, verticalAlign: 'text-bottom', animation: 'yyyBlink 1s infinite' }} />
        </p>
      </div>
      <div>
        <SecLabel>Key discussion points</SecLabel>
        <ShimmerLine w="92%" /><ShimmerLine w="78%" /><ShimmerLine w="85%" />
      </div>
    </div>
  );
}

// ============================================================ Transcript
function TranscriptReader() {
  const lines = [
    ['0:00', 'Okay — can everyone hear me? Let me share the rollout doc.'],
    ['0:11', "Yep, you're coming through clearly. Go ahead."],
    ['0:18', 'So the risk engine is feature-complete on staging as of this morning.'],
    ['0:27', 'The open question is whether we flip it on for the whole book, or start with the lower-limit accounts and watch it for a week.'],
    ['0:41', 'I would vote for the staged approach. We get the same signal with a fraction of the blast radius.'],
    ['0:52', 'Agreed. Let me write up a go / no-go checklist and we decide Thursday.'],
    ['1:04', 'One thing — who owns the rollback runbook if it misbehaves overnight?'],
    ['1:12', "I'll take it. I'll have a draft in the shared folder by tomorrow."],
  ];
  return (
    <div style={{ padding: '30px 40px', maxWidth: 700 }}>
      <h1 style={{ margin: '0 0 4px', fontFamily: DISP, fontWeight: 700, fontSize: 26, color: P.ink, letterSpacing: -0.5 }}>Risk engine rollout — go / no-go</h1>
      <div style={{ fontFamily: UI, fontSize: 12.5, color: P.muted, fontWeight: 500, marginBottom: 24 }}>Jun 10, 2026 · 1:31 PM · Risk Engine · 24m 18s</div>
      {lines.map(([t, s], i) => (
        <div key={i} style={{ display: 'flex', gap: 16, marginBottom: 13 }}>
          <span style={{ fontFamily: UI, fontSize: 12.5, fontWeight: 600, color: P.subtle, fontVariantNumeric: 'tabular-nums', width: 34, flex: '0 0 auto', paddingTop: 2 }}>{t}</span>
          <span style={{ fontFamily: UI, fontSize: 15, lineHeight: 1.6, color: P.inkSoft }}>{s}</span>
        </div>
      ))}
    </div>
  );
}

// ============================================================ Generate CTA
function GenerateCTAReader() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 18, padding: 40, textAlign: 'center' }}>
      <span style={{ width: 60, height: 60, borderRadius: 18, background: P.yellow,
        border: `1px solid ${P.yellowDeep}`, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        color: P.ink, boxShadow: '0 6px 18px rgba(200,160,20,0.3)' }}><Sparkle s={28} /></span>
      <div>
        <div style={{ fontFamily: DISP, fontWeight: 700, fontSize: 22, color: P.ink, letterSpacing: -0.4 }}>Turn this into clean notes</div>
        <div style={{ fontFamily: UI, fontSize: 14.5, color: P.muted, lineHeight: 1.55, maxWidth: 360, marginTop: 8 }}>
          You have a transcript. Generate a summary, decisions and action items — written locally on your machine.
        </div>
      </div>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '13px 24px',
        borderRadius: 12, background: P.yellow, border: `1px solid ${P.yellowDeep}`,
        boxShadow: '0 2px 0 rgba(180,140,10,0.35), 0 8px 20px rgba(200,160,20,0.32)',
        fontFamily: UI, fontWeight: 700, fontSize: 15, color: P.ink }}>
        <Sparkle s={17} />Generate AI meeting notes
      </span>
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, fontFamily: UI, fontSize: 12, fontWeight: 600, color: P.subtle }}>
        <Lock s={13} />Runs locally with llama3.2 · nothing leaves your PC
      </div>
    </div>
  );
}

// ============================================================ Welcome / empty
function WelcomeReader() {
  const steps = [['1', 'Record', 'One button captures you + everyone on the call'], ['2', 'Transcribe', 'Turned into text on your machine'], ['3', 'AI notes', 'A clean summary, decisions & action items']];
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 22, padding: 40, textAlign: 'center' }}>
      <Bird size={72} />
      <div>
        <div style={{ fontFamily: DISP, fontWeight: 700, fontSize: 26, color: P.ink, letterSpacing: -0.5 }}>Ready when you are</div>
        <div style={{ fontFamily: UI, fontSize: 15, color: P.muted, lineHeight: 1.55, maxWidth: 380, marginTop: 8 }}>
          Press <b style={{ color: P.inkSoft }}>Start recording</b> in the sidebar to capture your first conversation.
        </div>
      </div>
      <div style={{ display: 'flex', gap: 12, marginTop: 6 }}>
        {steps.map(([n, t, d]) => (
          <div key={n} style={{ width: 168, padding: '16px 14px', borderRadius: 14, background: P.surface,
            border: `1px solid ${P.border}`, textAlign: 'left' }}>
            <span style={{ width: 24, height: 24, borderRadius: 999, background: P.yellow, border: `1px solid ${P.yellowDeep}`,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily: DISP, fontWeight: 700, fontSize: 13, color: P.ink }}>{n}</span>
            <div style={{ fontFamily: UI, fontSize: 14, fontWeight: 700, color: P.ink, marginTop: 10 }}>{t}</div>
            <div style={{ fontFamily: UI, fontSize: 12, color: P.muted, lineHeight: 1.45, marginTop: 4 }}>{d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================ full screens
const recItem = (
  <div style={{ borderRadius: 12, background: 'rgba(229,72,77,0.08)', border: `1px solid rgba(229,72,77,0.28)`,
    padding: '12px 14px', marginBottom: 3, display: 'flex', alignItems: 'center', gap: 10 }}>
    <span style={{ width: 9, height: 9, borderRadius: 999, background: P.record, animation: 'yyyPulse 1.4s infinite', flex: '0 0 auto' }} />
    <div style={{ flex: 1 }}>
      <div style={{ fontFamily: UI, fontSize: 13.5, fontWeight: 700, color: P.ink }}>Recording…</div>
      <div style={{ fontFamily: UI, fontSize: 11.5, color: P.record, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>00:42 · No project</div>
    </div>
  </div>
);

const ScreenIdle = () => <RailShell reader={<NotesReader pad="34px 44px" maxWidth={620} />} />;
const ScreenRecording = () => <RailShell state="recording" timer="00:42" topItem={recItem} tabs={null} actions={false} reader={<RecordingReader />} readerBg={P.paper} />;
const ScreenProcessing = () => <RailShell state="processing" tabs={null} actions={false} reader={<ProcessingReader />} />;
const ScreenGenerating = () => <RailShell tabs={null} actions={false} reader={<GeneratingReader />} />;
const ScreenTranscript = () => <RailShell tabs="transcript" reader={<TranscriptReader />} />;
const ScreenGenerateCTA = () => <RailShell tabs="notes" actions={false} reader={<GenerateCTAReader />} />;
const ScreenWelcome = () => <RailShell state="idle" emptyList tabs={null} actions={false} reader={<WelcomeReader />} />;

Object.assign(window, {
  RecordingReader, ProcessingReader, GeneratingReader, TranscriptReader,
  GenerateCTAReader, WelcomeReader, Waveform,
  ScreenIdle, ScreenRecording, ScreenProcessing, ScreenGenerating,
  ScreenTranscript, ScreenGenerateCTA, ScreenWelcome,
});
