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
  const [lang, setLang] = useState('en');
  const [i18nReady, setI18nReady] = useState(!!window.I18N.bundles);
  useEffect(() => {
    if (!i18nReady) window.I18N._ready.then(() => setI18nReady(true));
  }, []);
  const t = useMemo(() => window.makeT(lang), [lang, i18nReady]);
  const [active, setActive] = useState('crop');
  const [profile, setProfile] = useState({
    name:    'Ramesh Kumar',
    village: 'Nandyal',
    state:   'Andhra Pradesh',
    phone:   '',
    crop:    'Cotton',
  });

  // tab bloom transition
  const [displayTab, setDisplayTab] = useState(active);
  const [phase, setPhase] = useState('idle');
  const wrapRef = useRef(null);

  function switchTab(next) {
    if (next === displayTab) return;
    setPhase('leaving');
    setTimeout(() => {
      setDisplayTab(next);
      setPhase('entering');
      setTimeout(() => setPhase('idle'), 290);
    }, 180);
    setActive(next);
  }

  // mount caterpillar once
  useEffect(() => {
    const host = document.getElementById('catHost');
    if (host && typeof mountCaterpillar === 'function') mountCaterpillar(host);
  }, []);

  // persist sidebar collapse on layout
  useEffect(() => {
    const layout = document.querySelector('.layout');
    if (layout) layout.classList.toggle('collapsed', collapsed);
  }, [collapsed]);

  const ViewComponent = VIEW_MAP[displayTab] || ViewCrop;

  return (
    <>
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
        />
        <main className="main">
          <TabBar active={active} setActive={switchTab} t={t} />
          <div className="tab-content-wrap" ref={wrapRef}>
            <div className={`tab-content ${phase !== 'idle' ? phase : ''}`}>
              <ViewComponent profile={profile} setProfile={setProfile} lang={lang} t={t} />
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

const rootEl = document.getElementById('root');
ReactDOM.createRoot(rootEl).render(<App />);
