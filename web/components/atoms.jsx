// atoms.jsx — shared UI primitives: Slider, Donut, LocationBar, VineBackdrop,
//             Sidebar, TabBar, Topbar, mountCaterpillar, Loading, ErrorCard,
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
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(42,51,40,0.08)" strokeWidth={stroke}/>
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

/* VineBackdrop is now in HTML (fixed layers); keep stub for compat */
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
];

function Sidebar({ collapsed, setCollapsed, profile, setProfile, lang, setLang, active, setActive, t }){
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
          <div style={{marginTop:'auto',padding:'12px 12px',background:'rgba(199,214,189,0.32)',borderRadius:12,fontSize:12,color:'var(--ink-soft)',lineHeight:1.6}}>
            <div style={{fontFamily:'var(--hand)',fontSize:18,color:'var(--ink)',marginBottom:4}}>today on the farm</div>
            ☀️ 29.4°C, 64% humidity<br/>
            🌧 light rain at dusk<br/>
            🐝 bees active · safe to spray after 5pm
          </div>
          <div style={{fontFamily:'var(--hand)',fontSize:16,color:'var(--ink-faint)',textAlign:'center',padding:'4px 6px',lineHeight:1.3}}>
            "a calm field today<br/>is a good harvest tomorrow."
          </div>
        </div>
      </div>
    </aside>
  );
}

/* ===== Centered horizontal tab bar ===== */
function TabBar({ active, setActive, t }){
  const tabs = [
    { k:'crop',       label:'Crop Advisor' },
    { k:'disease',    label:'Leaf Doctor' },
    { k:'market',     label:'Market Prices' },
    { k:'irrigation', label:'Watering' },
    { k:'acoustic',   label:'Listen to Field' },
    { k:'field',      label:'Field Watch' },
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

/* ============ Caterpillar — context-aware mechanic ============ */
function mountCaterpillar(host){
  if(!host || host.dataset.mounted) return;
  host.dataset.mounted = '1';
  const cat = document.createElement('div');
  cat.className = 'cat';
  cat.innerHTML = `
    <svg class="cat-svg" width="140" height="64" viewBox="0 0 140 64">
      <!-- antennae -->
      <g class="seg antennae">
        <line x1="100" y1="22" x2="106" y2="6" stroke="#3E6B3E" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="106" cy="6" r="2.2" fill="#B6553A"/>
        <line x1="106" y1="22" x2="114" y2="8" stroke="#3E6B3E" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="114" cy="8" r="2.2" fill="#B6553A"/>
      </g>
      <!-- body segments (back to front) -->
      <g class="seg body"><circle cx="20" cy="35" r="7" fill="#82B082"/><ellipse cx="20" cy="38" rx="5" ry="2" fill="#C7D6BD" opacity="0.6"/></g>
      <g class="seg body"><circle cx="34" cy="34" r="8" fill="#3E6B3E"/><ellipse cx="34" cy="37" rx="6" ry="2.5" fill="#C7D6BD" opacity="0.6"/></g>
      <g class="seg body"><circle cx="49" cy="33" r="8.5" fill="#82B082"/><ellipse cx="49" cy="36" rx="6.5" ry="2.5" fill="#C7D6BD" opacity="0.6"/></g>
      <g class="seg body"><circle cx="65" cy="32" r="9" fill="#3E6B3E"/><ellipse cx="65" cy="35" rx="7" ry="3" fill="#C7D6BD" opacity="0.6"/></g>
      <g class="seg body"><circle cx="82" cy="30" r="10" fill="#82B082"/><ellipse cx="82" cy="33" rx="7.5" ry="3" fill="#C7D6BD" opacity="0.6"/></g>
      <!-- head -->
      <g class="seg body head">
        <circle cx="100" cy="28" r="11" fill="#3E6B3E"/>
        <ellipse cx="100" cy="32" rx="8" ry="3" fill="#C7D6BD" opacity="0.6"/>
        <circle class="eye-w" cx="96" cy="25" r="2.8" fill="#FBF7EC"/>
        <circle class="pupil" cx="96" cy="25" r="1.5" fill="#2A3328"/>
        <ellipse class="lid" cx="96" cy="25" rx="2.8" ry="2.8" fill="#3E6B3E"/>
        <path class="mouth" d="M95 32 q5 2 10 0" stroke="#2A3328" stroke-width="1.2" fill="none" stroke-linecap="round"/>
        <!-- rosy cheek -->
        <circle cx="92" cy="30" r="2" fill="#B6553A" opacity="0.35"/>
      </g>
      <!-- tiny legs -->
      <g stroke="#3E6B3E" stroke-width="1.2" stroke-linecap="round">
        <line x1="20" y1="42" x2="20" y2="46"/><line x1="34" y1="42" x2="34" y2="46"/>
        <line x1="49" y1="42" x2="49" y2="46"/><line x1="65" y1="41" x2="65" y2="45"/>
        <line x1="82" y1="40" x2="82" y2="44"/><line x1="100" y1="39" x2="100" y2="43"/>
      </g>

      <!-- WRENCH (held in front legs) -->
      <g class="tool wrench">
        <g transform="translate(0 0)">
          <!-- wrench shaft -->
          <rect x="92" y="14" width="3" height="14" fill="#8C9684" rx="0.6"/>
          <!-- wrench head (open jaw) -->
          <path d="M88 8 L88 16 L91 16 L91 11 L97 11 L97 16 L100 16 L100 8 Z" fill="#8C9684"/>
          <circle cx="93.5" cy="13.5" r="1" fill="#5A6655"/>
          <!-- handle wrap -->
          <rect x="92" y="22" width="3" height="6" fill="#B6553A" rx="0.6"/>
        </g>
        <!-- front leg gripping wrench -->
        <line x1="100" y1="33" x2="96" y2="28" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>
      </g>

      <!-- MAGNIFYING LENS (held up by front legs) -->
      <g class="tool lens">
        <!-- handle -->
        <line x1="106" y1="26" x2="118" y2="38" stroke="#5A6655" stroke-width="2.2" stroke-linecap="round"/>
        <!-- ring -->
        <circle cx="104" cy="14" r="9" fill="rgba(199,214,189,0.35)" stroke="#5A6655" stroke-width="1.8"/>
        <circle cx="104" cy="14" r="9" fill="none" stroke="#FBF7EC" stroke-width="0.6"/>
        <!-- glint -->
        <path class="glint" d="M99 10 q3 -3 7 -3" stroke="#FFFCF1" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0"/>
        <!-- raised front legs -->
        <line x1="100" y1="22" x2="100" y2="16" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>
        <line x1="100" y1="16" x2="104" y2="14" stroke="#3E6B3E" stroke-width="1.6" stroke-linecap="round"/>
      </g>
    </svg>`;
  host.appendChild(cat);

  const pupil = cat.querySelector('.pupil');
  const mouth = cat.querySelector('.mouth');
  const head = cat.querySelector('.head');

  // smooth follow
  let curX = window.innerWidth*0.3;
  let targetX = curX;
  let mouseX = curX, mouseY = window.innerHeight/2;
  let facing = 1;
  let mood = 'idle';
  let moodUntil = 0;

  window.__catMood = (m, ms=1500)=>{
    mood = m; moodUntil = performance.now()+ms;
    cat.classList.toggle('excited', m==='excited');
    cat.classList.toggle('thinking', m==='thinking');
  };

  // ===== Tool detection: any slider drag → wrench, any input focus / file drop → lens =====
  let activeSlider = null;
  function setTool(t){
    cat.classList.toggle('tool-wrench', t==='wrench');
    cat.classList.toggle('tool-lens', t==='lens');
    if(!t){ cat.classList.remove('tool-wrench','tool-lens'); }
  }
  function satisfiedBounce(){
    cat.classList.add('bounce');
    setTimeout(()=>cat.classList.remove('bounce'), 500);
  }
  function antennaeWiggle(){
    cat.classList.add('antwig');
    setTimeout(()=>cat.classList.remove('antwig'), 1000);
  }

  document.addEventListener('pointerdown', (e)=>{
    const el = e.target;
    if(el.matches && el.matches('input[type=range]')){
      activeSlider = el; setTool('wrench');
    }
  }, true);
  document.addEventListener('pointerup', ()=>{
    if(activeSlider){ activeSlider=null; setTool(null); satisfiedBounce(); }
  }, true);
  document.addEventListener('focusin', (e)=>{
    const el = e.target;
    if(el.matches && el.matches('input:not([type=range]), textarea, select')){
      setTool('lens');
    }
  }, true);
  document.addEventListener('focusout', (e)=>{
    const el = e.target;
    if(el.matches && el.matches('input:not([type=range]), textarea, select')){
      setTool(null); antennaeWiggle();
    }
  }, true);
  // file inputs
  document.addEventListener('change', (e)=>{
    if(e.target.type==='file'){ setTool(null); antennaeWiggle(); }
  }, true);
  // drop zone hovers — peek with lens
  document.addEventListener('dragenter', ()=>setTool('lens'), true);
  document.addEventListener('dragleave', ()=>setTool(null), true);
  document.addEventListener('drop', ()=>{ setTool(null); antennaeWiggle(); }, true);

  // mouse tracking
  window.addEventListener('mousemove', e=>{
    mouseX = e.clientX; mouseY = e.clientY;
    targetX = Math.max(20, Math.min(window.innerWidth-140, mouseX - 70));
  });
  window.addEventListener('click', ()=>{ window.__catMood('excited',900); });

  // periodic blink
  setInterval(()=>{
    if(!cat.classList.contains('tool-lens') && !cat.classList.contains('tool-wrench')){
      cat.classList.add('blink');
      setTimeout(()=>cat.classList.remove('blink'), 320);
    }
  }, 8000);

  function frame(now){
    if (now > moodUntil && mood !== 'idle') { mood='idle'; cat.classList.remove('excited','thinking'); }
    const dx = targetX - curX;
    curX += dx * 0.06;
    const moving = Math.abs(dx) > 1.5;
    const desiredFacing = (mouseX > curX + 70) ? 1 : -1;
    if (desiredFacing !== facing && moving) facing = desiredFacing;
    cat.style.transform = `translateX(${curX}px) scaleX(${facing})`;

    // pupil tracks cursor
    const headRect = head.getBoundingClientRect();
    const hx = headRect.left + headRect.width/2;
    const hy = headRect.top + headRect.height/2;
    const ang = Math.atan2(mouseY-hy, (mouseX-hx)*facing);
    const px = Math.cos(ang)*1.6;
    const py = Math.sin(ang)*1.6;
    pupil.setAttribute('cx', 96 + px);
    pupil.setAttribute('cy', 25 + py);

    if (cat.classList.contains('tool-wrench')) mouth.setAttribute('d', 'M95 32 q5 0 10 0');
    else if (cat.classList.contains('tool-lens')) mouth.setAttribute('d', 'M96 32 q4 1 8 0');
    else if (mood==='excited') mouth.setAttribute('d', 'M93 31 q7 5 14 0');
    else if (mood==='thinking') mouth.setAttribute('d', 'M95 33 q5 -1 10 0');
    else mouth.setAttribute('d', 'M95 32 q5 2 10 0');

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

/* ============ New shared helpers ============ */
function Loading({ label }) {
  return (
    <div className="card rise" style={{textAlign:'center',padding:'40px 24px',background:'rgba(199,214,189,0.3)'}}>
      <div style={{fontSize:32,marginBottom:12}}>🌿</div>
      <div style={{color:'var(--ink-soft)',fontSize:14,fontStyle:'italic'}}>{label || 'Loading…'}</div>
    </div>
  );
}

function ErrorCard({ title, detail, onRetry }) {
  return (
    <div className="card rise" style={{borderColor:'var(--berry)',background:'rgba(182,85,58,0.06)'}}>
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
  const kindColor = {info:'var(--leaf)', warn:'#A06B1F', error:'var(--berry)'};
  return (
    <div style={{position:'fixed',top:16,right:16,display:'flex',flexDirection:'column',gap:8,zIndex:9999}}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background:'#FFFCF1',border:`1px solid ${kindColor[t.kind]||kindColor.info}`,
          color:kindColor[t.kind]||kindColor.info,
          borderRadius:999,padding:'8px 16px',fontSize:13,fontWeight:500,
          boxShadow:'0 4px 16px -4px rgba(42,51,40,0.2)',
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
  Sidebar, TabBar, Topbar, mountCaterpillar,
  Loading, ErrorCard, useToast, ToastContainer
});
