// Main App component — mounts the KisanOS layout
const { useState, useEffect, useRef, useMemo } = React;

const VIEW_MAP = {
  crop:       ViewCrop,
  disease:    ViewDisease,
  market:     ViewMarket,
  irrigation: ViewIrrigation,
  acoustic:   ViewAcoustic,
  field:      ViewField,
};

const CRUMB_MAP = {
  crop:       'Crop Advisor',
  disease:    'Leaf Doctor',
  market:     'Market Prices',
  irrigation: 'Watering',
  acoustic:   'Listen to Field',
  field:      'Field Watch',
};

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [lang, setLang] = useState(() => {
    try {
      const saved = localStorage.getItem('kisanos.lang');
      return (saved && window.isSupportedLang && window.isSupportedLang(saved)) ? saved : 'en';
    } catch { return 'en'; }
  });
  useEffect(() => {
    document.documentElement.lang = lang;
    window.__lang = lang;
  }, [lang]);

  useEffect(() => {
    try { localStorage.setItem('kisanos.lang', lang); } catch {}
  }, [lang]);
  const [i18nReady, setI18nReady] = useState(!!window.I18N.bundles);
  useEffect(() => {
    if (!i18nReady) window.I18N._ready.then(() => setI18nReady(true));
  }, []);
  const t = useMemo(() => window.makeT(lang), [lang, i18nReady]);
  // Auth: a JWT in localStorage (key `kisanos.token`) whose `exp` claim
  // is still in the future. Garbage / forged / expired tokens fail the
  // decode-and-check and route the user to Login.
  const [authed, setAuthed] = useState(() => window.auth?.isTokenValid(window.auth?.getToken()) || false);
  useEffect(() => {
    document.body.dataset.auth = authed ? 'app' : 'login';
  }, [authed]);
  // If api.js drops the token on a 401, mirror that into local state.
  useEffect(() => {
    const handler = () => setAuthed(false);
    window.addEventListener('kisanos:auth-expired', handler);
    return () => window.removeEventListener('kisanos:auth-expired', handler);
  }, []);
  const [active, setActive] = useState('crop');
  useEffect(() => {
    if (authed) document.body.dataset.tab = active;
    else document.body.removeAttribute('data-tab');
  }, [active, authed]);
  const [profile, setProfile] = useState({
    name:    'Ramesh Kumar',
    village: 'Bengaluru',
    state:   'Karnataka',
    phone:   '',
    crop:    'Cotton',
  });

  const [areaAcres, setAreaAcres] = useState(1.0);

  // Shared live field-watch data, prefetched on village change so every tab
  // (irrigation, crop, field) can read weather/flood/fire without re-fetching.
  const [fieldData, setFieldData] = useState(null);
  const [fieldLoading, setFieldLoading] = useState(false);
  const fieldFetchRef = useRef({ city: '', timer: null });
  useEffect(() => {
    const city = (profile.village || '').trim();
    if (fieldFetchRef.current.timer) clearTimeout(fieldFetchRef.current.timer);
    if (city.length < 2) { setFieldData(null); return; }
    if (city.toLowerCase() === fieldFetchRef.current.city) return;
    fieldFetchRef.current.timer = setTimeout(async () => {
      setFieldLoading(true);
      try {
        const data = await window.api.fieldWatchScan(city);
        fieldFetchRef.current.city = city.toLowerCase();
        setFieldData(data);
      } catch (_) {
        setFieldData(null);
      } finally {
        setFieldLoading(false);
      }
    }, 400);
    return () => clearTimeout(fieldFetchRef.current.timer);
  }, [profile.village]);

  // tab bloom transition
  const [displayTab, setDisplayTab] = useState(active);
  const [phase, setPhase] = useState('idle');
  const wrapRef = useRef(null);

  function switchTab(next) {
    if (next === displayTab) return;
    if (phase !== 'idle') return;
    setPhase('leaving');
    setTimeout(() => {
      setDisplayTab(next);
      setPhase('entering');
      setTimeout(() => setPhase('idle'), 340);
    }, 165);
    setActive(next);
  }

  // persist sidebar collapse on layout
  useEffect(() => {
    const layout = document.querySelector('.layout');
    if (layout) layout.classList.toggle('collapsed', collapsed);
  }, [collapsed]);

  const ViewComponent = VIEW_MAP[displayTab] || ViewCrop;

  function handleSignIn(creds) {
    // Login.jsx has already stored the JWT via window.auth.setToken on
    // successful OTP verification. Here we just sync derived state.
    if (creds && creds.phone) {
      setProfile(p => ({ ...p, phone: creds.phone }));
    }
    setAuthed(true);
  }

  function handleLogout() {
    window.auth?.clearToken();
    setAuthed(false);
    setActive('crop');
  }

  if (!authed) {
    return <Login onSignIn={handleSignIn} t={t} />;
  }

  return (
    <>
      <button
        className={`sb-fab ${collapsed ? 'is-collapsed' : 'is-open'}`}
        onClick={() => setCollapsed(c => !c)}
        aria-label={collapsed ? 'Open sidebar' : 'Close sidebar'}
        aria-pressed={!collapsed}
        title={collapsed ? 'Open sidebar' : 'Close sidebar'}
      >
        <span className="sb-fab-bar" />
        <span className="sb-fab-bar" />
        <span className="sb-fab-bar" />
      </button>
      <div className={`layout${collapsed ? ' collapsed' : ''}`}>
        <Sidebar
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          profile={profile}
          setProfile={setProfile}
          lang={lang}
          setLang={setLang}
          active={active}
          setActive={switchTab}
          t={t}
          onLogout={handleLogout}
        />
        <main className="main">
          <TabBar active={active} setActive={switchTab} t={t} />
          <div className="tab-content-wrap" ref={wrapRef}>
            <div className={`tab-content ${phase !== 'idle' ? phase : ''}`}>
              <ViewComponent profile={profile} setProfile={setProfile} lang={lang} t={t} fieldData={fieldData} fieldLoading={fieldLoading} areaAcres={areaAcres} setAreaAcres={setAreaAcres} />
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

const rootEl = document.getElementById('root');
ReactDOM.createRoot(rootEl).render(<App />);
