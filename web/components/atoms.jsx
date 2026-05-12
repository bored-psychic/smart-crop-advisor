// atoms.jsx — shared UI primitives: Slider, Donut, LocationBar,
//             Sidebar, TabBar, Topbar, Loading, ErrorCard,
//             useToast, ToastContainer
const { useState, useEffect, useRef, useMemo, useCallback } = React;

/* ============ Atoms ============ */
function Slider({ label, unit, min, max, step=1, value, onChange, hint }){
  const pct = ((value-min)/(max-min))*100;
  return (
    <div className="field">
      <div className="field-label">
        <span className="name">{label}</span>
        <span className="val">{value}<span style={{fontSize:12,color:'var(--ink-faint)',marginLeft:4}}>{unit}</span></span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e=>onChange(parseFloat(e.target.value))}
        style={{'--p':pct+'%'}}/>
      {hint && <div style={{fontSize:11,color:'var(--ink-faint)',marginTop:4,fontStyle:'italic'}}>{hint}</div>}
    </div>
  );
}

function Donut({ value, max=100, size=160, label, sub }){
  const stroke=10; const r=(size-stroke*2)/2; const c=2*Math.PI*r;
  const dash = c*Math.max(0,Math.min(1,value/max));
  return (
    <div style={{position:'relative',width:size,height:size,margin:'0 auto'}}>
      <svg width={size} height={size} style={{transform:'rotate(-90deg)'}}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth={stroke}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--leaf)" strokeWidth={stroke}
          strokeDasharray={`${dash} ${c-dash}`} strokeLinecap="round" style={{transition:'stroke-dasharray 1s ease'}}/>
      </svg>
      <div className="donut-num">
        <div className="bignum"><em>{Math.round(value)}</em><span className="unit">%</span></div>
        <div style={{fontSize:11,color:'var(--ink-faint)',marginTop:4,letterSpacing:'0.06em',textTransform:'uppercase'}}>{label}</div>
        {sub && <div style={{fontSize:11,color:'var(--leaf)',marginTop:2,fontStyle:'italic'}}>{sub}</div>}
      </div>
    </div>
  );
}

const INDIA_STATES = ["Andhra Pradesh","Assam","Bihar","Chhattisgarh","Gujarat","Haryana","Himachal Pradesh","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra","Odisha","Punjab","Rajasthan","Tamil Nadu","Telangana","Uttar Pradesh","Uttarakhand","West Bengal"];

const ALL_CROPS = [
  "Wheat","Rice","Maize","Barley","Pearl Millet","Sorghum","Chickpea",
  "Pigeon Pea","Black Gram","Green Gram","Lentil","Mustard","Groundnut",
  "Soybean","Sunflower","Sesame","Castor","Cotton","Sugarcane","Jute",
  "Potato","Onion","Tomato","Banana","Coconut","Mango"
];

const CROP_KC_KEYS = [
  'Rice','Wheat','Maize','Chickpea','Kidneybeans','Pigeonpeas',
  'Mothbeans','Mungbean','Blackgram','Lentil','Pomegranate','Banana',
  'Mango','Grapes','Watermelon','Muskmelon','Apple','Orange','Papaya',
  'Coconut','Cotton','Jute','Coffee'
];

const CALAMITY_TIPS = {
  thunderstorm:['⚡ Move livestock to shelter','🚫 Stop all field work immediately','💧 Clear drainage channels'],
  rain:['🌱 Avoid fertilizer — will wash away','🌊 Create bunds around fields','📞 Contact agriculture office if flooding'],
  drizzle:['💧 Good for germination','🌱 Ideal time for transplanting','✅ Reduce irrigation today'],
  snow:['🌿 Cover sensitive crops with cloth','🔥 Light irrigation before frost protects roots','🌱 Avoid pruning until frost passes'],
  mist:['🍄 Watch for fungal disease','💊 Apply preventive fungicide','🌬️ Improve air circulation'],
  haze:['😷 Reduce outdoor work','💧 Increase irrigation — heat stress likely','🌿 Monitor crops for wilting'],
  clear:['☀️ Good day for spraying pesticides','🚜 Ideal for harvesting','💧 Check soil moisture levels'],
  clouds:['🌤️ Good day for transplanting','💧 Moderate irrigation needed','🌱 Apply fertilizers today'],
};

const PEST_META = {
  Bee:         { role:'pollinator', severity:'low',    icon:'🐝', roleLabel:'Pollinator' },
  Locust:      { role:'pest',       severity:'high',   icon:'🦗', roleLabel:'Pest' },
  Cicada:      { role:'pest',       severity:'medium', icon:'🟠', roleLabel:'Pest' },
  Cricket:     { role:'ambient',    severity:'low',    icon:'⚪', roleLabel:'Ambient' },
  Grasshopper: { role:'pest',       severity:'medium', icon:'🟠', roleLabel:'Pest' },
  Beetle:      { role:'pest',       severity:'medium', icon:'🪲', roleLabel:'Pest' },
  Wasp:        { role:'pest',       severity:'medium', icon:'🐝', roleLabel:'Pest' },
};

const ACOUSTIC_WARNING_LABELS = {
  too_short:        '⏱ Recording too short — need at least 3 seconds',
  below_noise_floor:'🔇 Too quiet — hold mic closer to the plant stem',
  truncated_to_20s: '✂️ Long recording — analyzed first 20 seconds',
  low_sample_rate:  '📉 Low sample rate may reduce accuracy',
  high_sample_rate: '📈 Sample rate resampled to 16 kHz',
};

const GOVT_HELPLINES = [
  ['Kisan Call Centre',     '18001801551', 'Free · 24/7 · All Indian languages'],
  ['PM Kisan Helpline',     '155261',      'PM Kisan scheme queries'],
  ['NDRF Emergency',        '1078',        'Flood, earthquake, disaster'],
  ['Ambulance',             '108',         'Medical emergency'],
  ['Police',                '100',         'Security / theft'],
  ['State Agriculture Dept','18004252',    'Disease outbreak reporting'],
];

function LocationBar({ village, setVillage, state, setState, extra }){
  return (
    <div className="locbar rise rise-1">
      <span className="pin">📍</span>
      <input className="input" value={village} onChange={e=>setVillage(e.target.value)} placeholder="Your village or town"/>
      <select className="input" value={state} onChange={e=>setState(e.target.value)}>
        {INDIA_STATES.map(s=><option key={s}>{s}</option>)}
      </select>
      {extra}
    </div>
  );
}

/* Compat stub — VineBackdrop no longer rendered */
function VineBackdrop(){ return null; }

/* ============ Sidebar — collapsible, with profile editor + language ============ */
const LANGS = [
  { code:'en', flag:'🇬🇧', label:'English' },
  { code:'hi', flag:'🇮🇳', label:'हिन्दी' },
  { code:'te', flag:'🇮🇳', label:'తెలుగు' },
  { code:'ta', flag:'🇮🇳', label:'தமிழ்' },
  { code:'kn', flag:'🇮🇳', label:'ಕನ್ನಡ' },
  { code:'bn', flag:'🇮🇳', label:'বাংলা' },
  { code:'mr', flag:'🇮🇳', label:'मराठी' },
  { code:'ml', flag:'🇮🇳', label:'മലയാളം' },
  { code:'gu', flag:'🇮🇳', label:'ગુજરાતી' },
  { code:'pa', flag:'🇮🇳', label:'ਪੰਜਾਬੀ' },
];

function Sidebar({ collapsed, setCollapsed, profile, setProfile, lang, setLang, active, setActive, t, onLogout }){
  const [langOpen, setLangOpen] = useState(false);
  const langRef = useRef(null);
  useEffect(()=>{
    function close(e){ if(langRef.current && !langRef.current.contains(e.target)) setLangOpen(false); }
    document.addEventListener('click', close); return ()=>document.removeEventListener('click', close);
  },[]);
  const langObj = LANGS.find(l=>l.code===lang) || LANGS[0];
  const initials = (profile.name||'?').split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase();

  return (
    <aside className="sidebar">
      {/* Toggle (pressed-leaf shape on edge) — wrapped so it stays visible despite overflow:hidden */}
      <div className="sb-toggle-host">
        <button className="sb-toggle" onClick={()=>setCollapsed(!collapsed)} aria-label="Toggle sidebar">
          <svg viewBox="0 0 28 28">
            <path className="leaf-shape" d="M14 2 C 22 2, 26 8, 26 14 C 26 22, 20 26, 14 26 C 8 26, 2 22, 2 14 C 2 8, 6 2, 14 2 Z M14 2 C 14 8, 14 20, 14 26"/>
            <path className="arrow" d={collapsed ? "M11 9 L17 14 L11 19" : "M17 9 L11 14 L17 19"}/>
          </svg>
        </button>
      </div>

      {/* Collapsed state — only a tiny leaf icon at top, no nav emoji column */}
      <div className="sb-collapsed-icon">
        <svg width="22" height="22" viewBox="0 0 34 34">
          <path d="M17 30 L17 14" stroke="var(--leaf)" strokeWidth="1.6" strokeLinecap="round"/>
          <path d="M17 18 C 8 18, 5 10, 5 10 C 5 10, 9 22, 17 22 Z" fill="#82B082"/>
          <path d="M17 14 C 26 14, 29 6, 29 6 C 29 6, 25 18, 17 18 Z" fill="#6B9B6B"/>
        </svg>
      </div>

      {/* Open state */}
      <div className="sb-content">
        <div className="sb-inner" style={{padding:0,gap:18,flex:1}}>
          <div className="sb-brand">
            <svg width="32" height="32" viewBox="0 0 34 34">
              <path d="M17 30 L17 14" stroke="var(--leaf)" strokeWidth="1.6" strokeLinecap="round"/>
              <path d="M17 18 C 8 18, 5 10, 5 10 C 5 10, 9 22, 17 22 Z" fill="#82B082"/>
              <path d="M17 14 C 26 14, 29 6, 29 6 C 29 6, 25 18, 17 18 Z" fill="#6B9B6B"/>
            </svg>
            <div>
              <div className="brand-name">Kisan<em>OS</em></div>
              <div className="brand-tag"><span className="live-dot"></span> a quiet companion</div>
            </div>
          </div>

          {/* Profile card — handwritten field journal */}
          <div className="profile-card">
            <div className="profile-row">
              <div className="avatar">{initials}</div>
              <div style={{flex:1,minWidth:0}}>
                <input className="profile-name-input" value={profile.name} onChange={e=>setProfile({...profile,name:e.target.value})} placeholder="your name"/>
                <div style={{fontSize:11,color:'var(--ink-faint)',marginTop:-2}}>farmer · since 2019</div>
              </div>
            </div>
            <div className="profile-field">
              <span className="ic">📍</span>
              <input value={profile.village} onChange={e=>setProfile({...profile,village:e.target.value})} placeholder="village"/>
            </div>
            <div className="profile-field">
              <span className="ic">📞</span>
              <input value={profile.phone} onChange={e=>setProfile({...profile,phone:e.target.value})} placeholder="phone"/>
            </div>
            <div className="profile-field">
              <span className="ic">🌱</span>
              <input value={profile.crop} onChange={e=>setProfile({...profile,crop:e.target.value})} placeholder="primary crop"/>
            </div>
          </div>

          {/* Language pill */}
          <div ref={langRef} style={{position:'relative'}}>
            <div style={{fontSize:10,letterSpacing:'0.14em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6,padding:'0 4px'}}>language</div>
            <button className={`lang-pill ${langOpen?'open':''}`} onClick={(e)=>{e.stopPropagation();setLangOpen(!langOpen)}}>
              <span className="flag">{langObj.flag}</span>
              <span>{langObj.label}</span>
              <svg className="chev" width="12" height="8" viewBox="0 0 12 8"><path d="M1 1 L6 6 L11 1" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/></svg>
            </button>
            {langOpen && (
              <div className="lang-menu">
                {LANGS.map(l=>(
                  <button key={l.code} className={l.code===lang?'active':''} onClick={()=>{setLang(l.code);setLangOpen(false)}}>
                    <span style={{fontSize:14}}>{l.flag}</span> {l.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Today snippet */}
          <div style={{
            marginTop:'auto',padding:'12px 14px',
            background:'var(--glass-bg)',border:'1px solid var(--glass-border)',
            borderRadius:12,fontSize:12,color:'var(--ink-soft)',lineHeight:1.7
          }}>
            <div style={{fontFamily:'var(--display)',fontSize:18,color:'var(--ink)',marginBottom:4,letterSpacing:'-0.01em'}}>today on the farm</div>
            ☀️ 29.4°C, 64% humidity<br/>
            🌧 light rain at dusk<br/>
            🐝 bees active · safe to spray after 5pm
          </div>
          <div style={{
            fontFamily:'var(--display)',fontSize:15,fontStyle:'italic',
            color:'var(--ink-faint)',textAlign:'center',padding:'4px 6px',lineHeight:1.4
          }}>
            "a calm field today<br/>is a good harvest tomorrow."
          </div>

          {/* Footer action — sign out */}
          <div className="sb-actions">
            <button className="sb-action danger" onClick={onLogout} title="Sign out">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <path d="M16 17l5-5-5-5"/>
                <path d="M21 12H9"/>
              </svg>
              <span>Sign out</span>
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}

/* ===== Centered horizontal tab bar ===== */
function TabBar({ active, setActive, t }){
  const tabs = [
    { k:'crop',       label: t('Crop Advisor') },
    { k:'disease',    label: t('Leaf Doctor') },
    { k:'market',     label: t('Market Prices') },
    { k:'irrigation', label: t('Watering') },
    { k:'acoustic',   label: t('Listen to Field') },
    { k:'field',      label: t('Field Watch') },
  ];
  return (
    <div className="tabbar-wrap">
      <div className="tabbar" role="tablist">
        {tabs.map(tab=>(
          <button key={tab.k} role="tab" aria-selected={active===tab.k}
            className={`tab-pill ${active===tab.k?'active':''}`}
            onClick={()=>setActive(tab.k)}>
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ============ Topbar (compact in main col) ============ */
function Topbar({ crumb }){
  const [t, setT] = useState(()=>new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}));
  useEffect(()=>{ const id=setInterval(()=>setT(new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})),30000); return ()=>clearInterval(id); },[]);
  return (
    <div className="topbar">
      <div className="crumb">KisanOS · {crumb}</div>
      <div className="live"><span className="dot" style={{width:8,height:8,borderRadius:'50%',background:'var(--leaf)'}}></span> live · {t}</div>
    </div>
  );
}

/* ============ New shared helpers ============ */
function Loading({ label }) {
  return (
    <div className="card rise" style={{textAlign:'center',padding:'40px 24px'}}>
      <div style={{fontSize:32,marginBottom:12}}>🌿</div>
      <div style={{color:'var(--ink-soft)',fontSize:14,fontStyle:'italic'}}>{label || 'Loading…'}</div>
    </div>
  );
}

function ErrorCard({ title, detail, onRetry }) {
  return (
    <div className="card rise" style={{borderColor:'rgba(232,112,95,0.32)',background:'rgba(232,112,95,0.14)'}}>
      <div style={{color:'var(--berry)',fontFamily:'var(--display)',fontSize:20,marginBottom:8}}>{title}</div>
      {detail && <div style={{color:'var(--ink-soft)',fontSize:14,marginBottom:12}}>{detail}</div>}
      {onRetry && <button className="btn" style={{borderColor:'var(--berry)',color:'var(--berry)'}} onClick={onRetry}>↺ Try again</button>}
    </div>
  );
}

// useToast hook + Toast component
let _toastId = 0;
function useToast() {
  const [toasts, setToasts] = useState([]);
  const add = useCallback((text, kind='info') => {
    const id = ++_toastId;
    setToasts(prev => [...prev, {id, text, kind}]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000);
  }, []);
  return { toasts, add };
}

function ToastContainer({ toasts }) {
  const kindColor = {info:'var(--leaf)', warn:'var(--sun)', error:'var(--berry)'};
  return (
    <div style={{position:'fixed',top:16,right:16,display:'flex',flexDirection:'column',gap:8,zIndex:9999}}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background:'rgba(8,18,10,0.88)',
          backdropFilter:'blur(20px)',
          WebkitBackdropFilter:'blur(20px)',
          border:'1px solid var(--glass-border)',
          color:kindColor[t.kind]||kindColor.info,
          borderRadius:999,padding:'8px 16px',fontSize:13,fontWeight:500,
          boxShadow:'0 8px 24px -8px rgba(0,0,0,0.5)',
          animation:'rise 0.3s ease both'
        }}>{t.text}</div>
      ))}
    </div>
  );
}

Object.assign(window, {
  Slider, Donut, INDIA_STATES, ALL_CROPS, CROP_KC_KEYS, CALAMITY_TIPS, PEST_META, ACOUSTIC_WARNING_LABELS,
  GOVT_HELPLINES,
  LocationBar, VineBackdrop, LANGS,
  Sidebar, TabBar, Topbar,
  Loading, ErrorCard, useToast, ToastContainer
});
