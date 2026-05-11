// Garden — atoms, sidebar, views (with location bars + audio dropzone + cursor caterpillar)
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
function _UnusedVineBackdrop(){
  // generate a denser set of vines + tendrils + leaves
  const big = [
    "M-40 60 C 200 110, 220 280, 80 360 S -40 520, 160 600 S 380 760, 220 880 S 60 1100, 280 1240 S 380 1380, 200 1500",
    "M1280 40 C 1040 120, 1020 320, 1180 420 S 1300 600, 1080 700 S 860 820, 1040 940 S 1240 1100, 1020 1220 S 920 1380, 1140 1520",
    "M620 -20 C 580 200, 660 360, 600 540 S 520 720, 620 880 S 700 1040, 580 1220 S 540 1380, 600 1540",
    "M-20 980 C 240 940, 360 820, 480 880 S 660 1020, 820 980 S 1100 880, 1280 940",
    "M-40 320 C 180 280, 320 380, 460 320 S 760 220, 940 300 S 1180 360, 1300 320",
  ];
  const leaves = [
    [80,180,8],[40,420,18],[160,620,-10],[110,840,12],[200,1050,4],[260,1240,-8],
    [1180,140,-14],[1110,380,8],[1220,620,-6],[1060,820,12],[1140,1050,-8],[1010,1240,16],
    [600,160,4],[600,420,-12],[600,680,8],[600,940,-10],[600,1180,12],
    [380,920,6],[700,920,-6],[860,940,12],[260,300,-14],[940,300,10],[1100,300,-8],
  ];
  const tendrils = [
    "M120 240 q 30 -20 60 -10 q 30 10 30 40",
    "M1080 480 q -30 -20 -60 -10 q -30 10 -30 40",
    "M520 760 q 30 -10 60 0",
    "M680 200 q 40 30 80 20",
    "M340 1100 q -40 30 -80 20",
  ];
  return (
    <>
      <div className="vines">
        <svg viewBox="0 0 1280 1600" preserveAspectRatio="none">
          {big.map((d,i)=>(
            <path key={i} d={d}
              className={`vine-path ${i>=3?'l3':i>=1?'l2':''}`}
              style={{ animationDelay:`${i*0.25}s` }}/>
          ))}
          {leaves.map(([x,y,rot],i)=>(
            <g key={i} className="leaf-svg sway"
              style={{ animationDelay:`${0.6+i*0.06}s`, transformOrigin:`${x}px ${y}px` }}
              transform={`translate(${x} ${y}) rotate(${rot})`}>
              <path d="M0 0 C 14 -14, 28 -10, 28 6 C 28 22, 12 26, 0 16 Z" fill="var(--leaf-2)" opacity="0.7"/>
              <path d="M0 0 C 10 -2, 20 0, 26 8" stroke="var(--leaf)" strokeWidth="0.8" fill="none" opacity="0.7"/>
            </g>
          ))}
        </svg>
      </div>
      <div className="creepers">
        <svg viewBox="0 0 1280 1600" preserveAspectRatio="none">
          {/* creeping micro-vines */}
          <path className="creep" d="M0 80 q 80 30 160 10 q 80 -25 160 5 q 80 30 160 0 q 80 -25 160 10 q 80 30 160 5 q 80 -20 160 5 q 80 30 160 0"/>
          <path className="creep b" d="M1280 240 q -90 25 -180 0 q -90 -25 -180 5 q -90 30 -180 -5 q -90 -25 -180 10 q -90 30 -180 0 q -90 -20 -180 10"/>
          <path className="creep c" d="M0 540 q 100 -30 200 0 q 100 30 200 -5 q 100 -25 200 10 q 100 30 200 -10 q 100 -20 200 5"/>
          <path className="creep" d="M1280 760 q -110 30 -220 0 q -110 -25 -220 5 q -110 30 -220 -5 q -110 -25 -220 10 q -110 30 -220 0"/>
          <path className="creep b" d="M0 1080 q 120 -30 240 5 q 120 30 240 -5 q 120 -25 240 10 q 120 30 240 -10 q 120 -20 240 5"/>
          <path className="creep c" d="M1280 1300 q -130 30 -260 0 q -130 -25 -260 5 q -130 30 -260 -5 q -130 -25 -260 10"/>
          {/* curly tendrils */}
          {[
            "M120 200 c 20 -10 40 0 50 20 c 8 18 -10 30 -25 24 c -14 -6 -10 -28 6 -30",
            "M1100 360 c -20 -10 -40 0 -50 20 c -8 18 10 30 25 24 c 14 -6 10 -28 -6 -30",
            "M340 720 c 18 -8 38 2 46 22 c 8 20 -12 30 -26 22 c -14 -8 -8 -28 6 -30",
            "M940 920 c -18 -8 -38 2 -46 22 c -8 20 12 30 26 22 c 14 -8 8 -28 -6 -30",
            "M260 1180 c 20 -10 40 0 50 20 c 8 18 -10 30 -25 24",
            "M1020 1240 c -20 -10 -40 0 -50 20 c -8 18 10 30 25 24",
          ].map((d,i)=><path key={i} className="tendril" d={d} style={{opacity:0.4}}/>)}
          {/* tiny creeper leaves */}
          {[[180,90,4],[420,110,-8],[660,80,12],[900,100,-6],[1140,90,8],
            [200,560,-10],[460,540,8],[760,560,-6],[1040,540,12],
            [120,1090,6],[400,1100,-8],[720,1080,12],[1000,1100,-6],
            [220,1310,4],[560,1300,-10],[860,1310,8]
          ].map(([x,y,rot],i)=>(
            <g key={'c'+i} className="creep-leaf sway"
              style={{ animationDelay:`${1.2+i*0.08}s`, transformOrigin:`${x}px ${y}px` }}
              transform={`translate(${x} ${y}) rotate(${rot})`}>
              <path d="M0 0 C 8 -8, 16 -6, 16 4 C 16 12, 8 14, 0 10 Z" fill="var(--leaf-2)" opacity="0.6"/>
            </g>
          ))}
        </svg>
      </div>
    </>
  );
}

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

/* ============ Crop ============ */
function classifyCrop({N,P,K,ph,temperature,humidity,rainfall}){
  const c=[
    {name:'rice',emoji:'🌾',score:(rainfall>=150?40:10)+(humidity>=70?25:8)+(temperature>=20&&temperature<=32?20:5)+(ph>=5.5&&ph<=7?10:3)+(N/3)},
    {name:'maize',emoji:'🌽',score:(rainfall>=60&&rainfall<=180?30:10)+(temperature>=18&&temperature<=30?25:8)+(N>=60?20:8)+(ph>=5.8&&ph<=7.5?15:5)},
    {name:'cotton',emoji:'🌿',score:(temperature>=22&&temperature<=34?28:6)+(rainfall>=60&&rainfall<=120?20:5)+(K>=20?14:5)+(ph>=6&&ph<=8?12:5)},
    {name:'chickpea',emoji:'🫘',score:(temperature>=15&&temperature<=28?28:6)+(rainfall<=80?22:5)+(P>=30?16:5)+(ph>=6&&ph<=8?14:5)},
    {name:'wheat',emoji:'🌾',score:(temperature>=10&&temperature<=24?32:6)+(humidity>=40&&humidity<=70?14:4)+(N>=70?18:6)+(ph>=6&&ph<=7.5?12:4)},
    {name:'banana',emoji:'🍌',score:(temperature>=24&&temperature<=32?28:5)+(humidity>=70?22:5)+(rainfall>=120?18:6)+(K>=40?14:4)},
    {name:'mango',emoji:'🥭',score:(temperature>=22&&temperature<=34?22:6)+(rainfall>=80&&rainfall<=180?16:6)+(ph>=5.5&&ph<=7.5?12:4)},
    {name:'coffee',emoji:'☕',score:(temperature>=18&&temperature<=26?28:5)+(humidity>=60?20:5)+(rainfall>=130?20:5)+(ph>=5&&ph<=6.5?14:4)},
  ];
  const t=c.reduce((s,x)=>s+x.score,0)||1;
  return c.map(x=>({...x,prob:x.score/t})).sort((a,b)=>b.prob-a.prob);
}

function ViewCrop({ profile, setProfile, t }){
  const [N,setN]=useState(90),[P,setP]=useState(42),[K,setK]=useState(43),[ph,setPh]=useState(6.5);
  const [temperature,setT]=useState(25),[humidity,setH]=useState(80),[rainfall,setR]=useState(200);
  const [result,setResult]=useState(null);
  const ranked = useMemo(()=>classifyCrop({N,P,K,ph,temperature,humidity,rainfall}),[N,P,K,ph,temperature,humidity,rainfall]);
  const top = result?.[0]; const conf = top ? top.prob*100 : 0;

  return (
    <div className="view-fade">
      <Topbar crumb="Crop Advisor"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">crop advisor</div>
          <h1 className="page-title">Find what your soil <em>wants to grow.</em></h1>
          <p className="page-lede">Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={<span className="tag">🌦 kharif season</span>}/>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>Soil</h3><span className="meta">npk · ph</span></div>
          <Slider label="Nitrogen"   unit="kg/ha" min={0} max={140} value={N} onChange={setN}  hint={N<40?'a little hungry':N<90?'just right':'plenty'}/>
          <Slider label="Phosphorus" unit="kg/ha" min={5} max={145} value={P} onChange={setP}/>
          <Slider label="Potassium"  unit="kg/ha" min={5} max={205} value={K} onChange={setK}/>
          <Slider label="Soil pH"    unit=""      min={3.5} max={9.5} step={0.1} value={ph} onChange={setPh} hint={ph<5.5?'acidic':ph<7.5?'sweet spot':'a touch alkaline'}/>
        </div>
        <div className="card rise rise-2">
          <div className="card-h"><h3>Weather</h3><span className="meta">your local feel</span></div>
          <Slider label="Temperature" unit="°C" min={8} max={45} step={0.5} value={temperature} onChange={setT}/>
          <Slider label="Humidity" unit="%" min={14} max={100} value={humidity} onChange={setH}/>
          <Slider label="Rainfall" unit="mm" min={20} max={300} step={5} value={rainfall} onChange={setR}/>
          <div style={{display:'flex',gap:10,marginTop:18}}>
            <button className="btn primary" onClick={()=>{ setResult(ranked); window.__catMood?.('excited',1500); }}>🌱 Suggest a crop</button>
            <button className="btn ghost" onClick={()=>{ setN(90);setP(42);setK(43);setPh(6.5);setT(25);setH(80);setR(200);setResult(null); }}>Reset</button>
          </div>
        </div>
      </div>

      {result && (
        <div className="card rise" style={{marginTop:18}}>
          <div className="grid-2" style={{gridTemplateColumns:'auto 1fr',alignItems:'center',gap:36}}>
            <Donut value={conf} label="confidence"/>
            <div>
              <div className="page-eyebrow">our recommendation</div>
              <div style={{fontFamily:'var(--display)',fontSize:60,letterSpacing:'-0.02em',color:'var(--ink)',marginTop:4,lineHeight:1.1}}>
                {top.emoji} <em style={{color:'var(--leaf)',fontStyle:'italic',fontWeight:300}}>{top.name}</em>
              </div>
              <p className="muted" style={{maxWidth:480,marginTop:10}}>Your soil and weather profile fits {top.name} the best. It should give a steady, healthy yield this season.</p>
              <div style={{display:'flex',gap:8,marginTop:12,flexWrap:'wrap'}}>
                <span className="tag">⛅ Kharif</span>
                <span className="tag">🌱 hardy yield</span>
                <span className="tag">💧 medium water</span>
              </div>
              <div style={{marginTop:22}}>
                <div className="page-eyebrow" style={{marginBottom:8}}>also great</div>
                <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
                  {result.slice(1,4).map(c=>(
                    <div key={c.name} className="tile" style={{padding:'10px 14px'}}>
                      <span style={{fontSize:18,marginRight:8}}>{c.emoji}</span>
                      <span style={{textTransform:'capitalize'}}>{c.name}</span>
                      <span style={{color:'var(--ink-faint)',marginLeft:8,fontSize:12}}>{(c.prob*100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ============ Disease ============ */
function ViewDisease({ profile, t }){
  const [crop,setCrop]=useState('Tomato');
  const [phase,setPhase]=useState('idle');
  const [progress,setProgress]=useState(0);
  const [result,setResult]=useState(null);
  const fileRef = useRef();
  const DISEASES={
    Tomato:{disease:'Early Blight', sci:'Alternaria solani', sev:'Medium', conf:87, treatment:'Mancozeb 75% WP @ 2g/L. Remove infected leaves. Repeat after 10 days.', prevention:'Crop rotation every 2 years. Use resistant varieties.'},
    Potato:{disease:'Late Blight', sci:'Phytophthora infestans', sev:'High', conf:92, treatment:'Cymoxanil + Mancozeb urgently. Destroy infected haulms.', prevention:'Well-drained soil. Watch the weather.'},
    Rice:  {disease:'Rice Blast',  sci:'Magnaporthe oryzae', sev:'High', conf:89, treatment:'Tricyclazole 75% WP @ 0.6g/L at booting stage.', prevention:'Resistant varieties. Avoid excess nitrogen.'},
    Cotton:{disease:'Pink Bollworm', sci:'Pectinophora gossypiella', sev:'High', conf:84, treatment:'Chlorpyrifos 50% + Cypermethrin 5% EC @ 2ml/L.', prevention:'Destroy crop residue. Pheromone traps early.'},
  };
  function run(){
    setPhase('scan');setProgress(0);setResult(null);
    window.__catMood?.('thinking', 2200);
    const id=setInterval(()=>setProgress(p=>{
      const np=p+5+Math.random()*6;
      if(np>=100){clearInterval(id);setPhase('done');setResult(DISEASES[crop]);return 100}
      return np;
    }),80);
  }
  const sevColor = result?.sev==='High' ? 'var(--berry)' : result?.sev==='Medium' ? '#A06B1F' : 'var(--leaf)';

  return (
    <div className="view-fade">
      <Topbar crumb="Leaf Doctor"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">leaf doctor</div>
          <h1 className="page-title">A <em>second pair of eyes</em> for sick leaves.</h1>
          <p className="page-lede">Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>Send a photo</h3><select className="input" style={{width:140}} value={crop} onChange={e=>setCrop(e.target.value)}>{Object.keys(DISEASES).map(k=><option key={k}>{k}</option>)}</select></div>
          <div className="drop" onClick={()=>fileRef.current?.click()}>
            <div style={{fontSize:36}}>🍃</div>
            <div style={{marginTop:10,fontSize:14}}><strong>Drop a leaf photo here</strong></div>
            <div className="muted small" style={{marginTop:4}}>or click to choose · jpg, png, webp</div>
            <input ref={fileRef} type="file" accept="image/*" style={{display:'none'}} onChange={()=>run()}/>
          </div>
          <div style={{display:'flex',gap:10,marginTop:14}}>
            <button className="btn primary" onClick={run} disabled={phase==='scan'}>{phase==='scan' ? 'Looking…' : '🔎 Try a sample'}</button>
            <button className="btn ghost">📸 Use camera</button>
          </div>
        </div>

        <div className="card rise rise-2">
          <div className="card-h"><h3>What we see</h3>{result && <span className="tag" style={{color:sevColor,borderColor:sevColor+'40',background:sevColor+'14'}}>severity · {result.sev}</span>}</div>
          {phase==='idle' && <div className="muted" style={{padding:'30px 0',textAlign:'center'}}>Send a photo and we'll have a look. 🌿</div>}
          {phase==='scan' && (
            <div>
              <div className="bar"><span style={{width:progress+'%'}}></span></div>
              <div className="muted small" style={{marginTop:10,fontStyle:'italic'}}>Looking at the leaf carefully…</div>
            </div>
          )}
          {phase==='done' && result && (
            <div className="rise">
              <div style={{fontFamily:'var(--display)',fontSize:30,color:'var(--ink)',letterSpacing:'-0.01em'}}>
                {result.disease}
              </div>
              <div className="small muted" style={{fontStyle:'italic',marginTop:2}}>{result.sci}</div>
              <div style={{marginTop:14,padding:'12px 14px',background:'rgba(199,214,189,0.4)',borderRadius:12}}>
                <div className="page-eyebrow" style={{color:'var(--leaf)'}}>treatment</div>
                <div style={{marginTop:4}}>{result.treatment}</div>
              </div>
              <div style={{marginTop:10,padding:'12px 14px',background:'rgba(217,182,107,0.18)',borderRadius:12}}>
                <div className="page-eyebrow" style={{color:'#A06B1F'}}>prevention</div>
                <div style={{marginTop:4}}>{result.prevention}</div>
              </div>
              <div style={{display:'flex',gap:8,marginTop:14}}>
                <button className="btn primary">📲 Send to WhatsApp</button>
                <button className="btn">🔊 Read aloud</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============ Market ============ */
function genSeries(b,n=60){let arr=[],p=b;for(let i=0;i<n;i++){p=p*(1+(Math.random()-0.48)*0.025+0.0008);arr.push(p)}return arr}
function ViewMarket({ profile, setProfile, t }){
  const [crop,setCrop]=useState('Cotton');
  const series=useMemo(()=>genSeries({Cotton:6800,Wheat:2400,Rice:2100,Maize:1850,Onion:2000,Tomato:1300}[crop]||3000,60),[crop]);
  const fc=useMemo(()=>genSeries(series[series.length-1],14),[series]);
  const today=series[series.length-1], yest=series[series.length-2];
  const change=((today-yest)/yest)*100, target=fc[fc.length-1], upside=((target-today)/today)*100;

  const W=720,H=220,pad=30;
  const all=[...series,...fc]; const min=Math.min(...all), max=Math.max(...all);
  const x=i=>pad+i*(W-pad*2)/(all.length-1);
  const y=v=>H-pad-((v-min)/(max-min))*(H-pad*2);
  const path=(arr,off=0)=>arr.map((v,i)=>`${i===0?'M':'L'}${x(i+off)},${y(v)}`).join(' ');

  return (
    <div className="view-fade">
      <Topbar crumb="Market"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">market</div>
          <h1 className="page-title">A <em>fair price,</em> a calm decision.</h1>
          <p className="page-lede">We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={
          <select className="input" value={crop} onChange={e=>setCrop(e.target.value)}>
            {['Cotton','Wheat','Rice','Maize','Onion','Tomato'].map(c=><option key={c}>{c}</option>)}
          </select>
        }/>

      <div className="card rise rise-2">
        <div className="card-h">
          <h3 style={{margin:0}}>Today's mandi · {crop}</h3>
          <span className="tag">📍 {profile.state}</span>
        </div>
        <div className="grid-3" style={{marginBottom:14}}>
          <div>
            <div className="page-eyebrow">spot price</div>
            <div className="bignum">₹<em>{today.toFixed(0)}</em><span className="unit">/q</span></div>
            <div className="small" style={{color:change>=0?'var(--leaf)':'var(--berry)',marginTop:4}}>{change>=0?'▲':'▼'} {Math.abs(change).toFixed(2)}% from yesterday</div>
          </div>
          <div>
            <div className="page-eyebrow">in 14 days</div>
            <div className="bignum">₹<em>{target.toFixed(0)}</em><span className="unit">/q</span></div>
            <div className="small" style={{color:upside>=0?'var(--leaf)':'var(--berry)',marginTop:4}}>{upside>=0?'▲':'▼'} {Math.abs(upside).toFixed(2)}% expected</div>
          </div>
          <div>
            <div className="page-eyebrow">our advice</div>
            <div className="bignum"><em style={{color:upside>2?'var(--leaf)':upside<-2?'var(--berry)':'#A06B1F'}}>{upside>2?'wait':upside<-2?'sell':'either way'}</em></div>
            <div className="small muted" style={{marginTop:4}}>{upside>2?`hold for ~₹${(target-today).toFixed(0)} more`:upside<-2?'price likely to slip':'pretty steady'}</div>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} style={{width:'100%',height:220,display:'block'}}>
          <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="rgba(62,107,62,0.18)"/><stop offset="100%" stopColor="rgba(62,107,62,0)"/></linearGradient></defs>
          {[0,1,2,3].map(i=><line key={i} x1={pad} y1={pad+i*(H-pad*2)/3} x2={W-pad} y2={pad+i*(H-pad*2)/3} stroke="rgba(42,51,40,0.06)"/>)}
          <path d={series.map((v,i)=>`${i===0?'M':'L'}${x(i)},${y(v)}`).join(' ')+` L${x(series.length-1)},${H-pad} L${x(0)},${H-pad} Z`} fill="url(#ag)"/>
          <path d={path(series,0)} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeLinecap="round"/>
          <path d={path(fc,series.length-1)} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeDasharray="3 5" strokeLinecap="round" opacity="0.7"/>
          <line x1={x(series.length-1)} y1={pad} x2={x(series.length-1)} y2={H-pad} stroke="var(--ink-faint)" strokeDasharray="2 4" opacity="0.3"/>
          <text x={x(series.length-1)+4} y={pad+10} className="spark-axis">today</text>
        </svg>
      </div>
    </div>
  );
}

/* ============ Irrigation ============ */
function ViewIrrigation({ profile, setProfile, t }){
  const KC={Rice:[1.05,1.20,1.20,0.90],Cotton:[0.35,0.70,1.20,0.50],Maize:[0.30,0.70,1.20,0.35],Tomato:[0.50,0.80,1.15,0.70],Wheat:[0.30,0.70,1.15,0.25]};
  const STAGES=['just sown','growing','flowering','ripening'];
  const [crop,setCrop]=useState('Cotton');
  const [stage,setStage]=useState(2);
  const [temp,setTemp]=useState(32),[hum,setHum]=useState(45),[wind,setWind]=useState(12),[area,setArea]=useState(2.4);
  const ET0=useMemo(()=>{
    const w=wind/3.6, es=0.6108*Math.exp(17.27*temp/(temp+237.3)), ea=es*hum/100, vpd=Math.max(es-ea,0);
    return Math.max(((0.408*0.0135*(temp+17.8)*(w+1))+(0.34*vpd*w))*4,1.0);
  },[temp,hum,wind]);
  const kc=KC[crop][stage]; const ETc=ET0*kc; const liters=ETc*area*10000;
  const nextHrs = Math.max(6, 48-ETc*4);

  return (
    <div className="view-fade">
      <Topbar crumb="Watering"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">water</div>
          <h1 className="page-title">Just enough water, <em>just in time.</em></h1>
          <p className="page-lede">We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={
          <select className="input" value={crop} onChange={e=>setCrop(e.target.value)}>
            {Object.keys(KC).map(c=><option key={c}>{c}</option>)}
          </select>
        }/>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>Your field</h3></div>
          <div className="field">
            <div className="field-label"><span className="name">Where the crop is</span></div>
            <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:8}}>
              {STAGES.map((s,i)=>(
                <button key={s} className={`tile ${stage===i?'active':''}`} style={{padding:'10px 8px',textAlign:'center',fontSize:12}} onClick={()=>setStage(i)}>{s}</button>
              ))}
            </div>
          </div>
          <Slider label="Temperature" unit="°C" min={5} max={48} step={0.5} value={temp} onChange={setTemp}/>
          <Slider label="Humidity" unit="%" min={10} max={100} value={hum} onChange={setHum}/>
          <Slider label="Plot size" unit="ha" min={0.1} max={20} step={0.1} value={area} onChange={setArea}/>
        </div>

        <div className="card rise rise-2">
          <div className="card-h"><h3>Today's plan</h3><span className="tag">gentle reminder</span></div>
          <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:18,padding:'10px 0'}}>
            <Donut value={Math.min(100, ETc*8)} label="thirst level" sub={`${ETc.toFixed(2)} mm/day`}/>
            <div style={{textAlign:'center'}}>
              <div className="bignum"><em>{Math.round(liters).toLocaleString()}</em> <span className="unit">L today</span></div>
              <div className="muted small" style={{marginTop:6}}>across {area} ha · ≈ {(liters/1000).toFixed(1)} m³</div>
            </div>
            <div style={{display:'flex',gap:10}}>
              <span className="tag">⏱ next watering · {Math.round(nextHrs)}h</span>
              <span className="tag warn">☀️ warm day</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============ Acoustic — drag-drop audio ============ */
function ViewAcoustic({ profile, t }){
  const [phase,setPhase]=useState('idle');
  const [bars,setBars]=useState(Array(40).fill(0.1));
  const [result,setResult]=useState(null);
  const [file,setFile]=useState(null);
  const [drag,setDrag]=useState(false);
  const inputRef = useRef();
  useEffect(()=>{
    if(phase==='listen'){
      const id=setInterval(()=>setBars(Array.from({length:40},()=>0.2+Math.random()*0.7)),100);
      return ()=>clearInterval(id);
    }
  },[phase]);
  function go(){
    setPhase('listen');setResult(null);
    window.__catMood?.('thinking', 2400);
    setTimeout(()=>{ setPhase('done'); setResult({name:'Stem Borer',sev:'high',early:'~7 days early',hint:'Set up pheromone traps. Check stems near the base.'}); },2400);
  }
  function handleFile(f){ if(!f) return; setFile(f); setPhase('idle'); setResult(null); }
  function onDrop(e){ e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files[0]); }
  return (
    <div className="view-fade">
      <Topbar crumb="Listen"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">listen</div>
          <h1 className="page-title">Hear the bugs <em>before they show.</em></h1>
          <p className="page-lede">Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>Upload a recording</h3><span className="tag">~6 seconds</span></div>
          <div className="drop"
            onClick={()=>inputRef.current?.click()}
            onDragOver={e=>{e.preventDefault();setDrag(true)}}
            onDragLeave={()=>setDrag(false)}
            onDrop={onDrop}
            style={{borderColor:drag?'var(--leaf)':'var(--line-2)',background:drag?'rgba(199,214,189,0.4)':'rgba(255,255,255,0.4)'}}>
            <div style={{fontSize:36}}>{file?'🎵':'🎙'}</div>
            <div style={{marginTop:10,fontSize:14}}>
              {file ? <strong>{file.name}</strong> : <strong>Drag &amp; drop your field audio here</strong>}
            </div>
            <div className="muted small" style={{marginTop:4}}>
              {file ? `${(file.size/1024).toFixed(0)} KB · ready` : 'or click to choose · wav · mp3 · m4a · ogg · webm'}
            </div>
            <input ref={inputRef} type="file" accept="audio/*" style={{display:'none'}} onChange={e=>handleFile(e.target.files[0])}/>
          </div>
          {file && <audio controls src={URL.createObjectURL(file)} style={{width:'100%',marginTop:12,borderRadius:10}}/>}
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:14,gap:10}}>
            <div className="muted small" style={{fontStyle:'italic'}}>tip: 15–30 cm from the stem · breathe slowly</div>
            <div style={{display:'flex',gap:8}}>
              <button className="btn" onClick={()=>{setFile(null);setResult(null);setPhase('idle')}}>clear</button>
              <button className="btn primary" onClick={go} disabled={phase==='listen'}>
                {phase==='listen'?'🎧 listening…':'🔊 analyze'}
              </button>
            </div>
          </div>
        </div>

        <div className="card rise rise-2">
          <div className="card-h"><h3>What we heard</h3>{result && <span className="tag alert">{result.sev}</span>}</div>
          <div style={{display:'flex',justifyContent:'center',alignItems:'flex-end',gap:3,height:120,padding:'10px 0'}}>
            {bars.map((b,i)=>(
              <div key={i} style={{width:5,height:`${Math.max(8,b*100)}%`,background:'var(--leaf-2)',borderRadius:2,transition:'height .12s ease',opacity:phase==='idle'?0.3:0.9}}/>
            ))}
          </div>
          {!result && phase!=='listen' && <div className="muted" style={{padding:'10px 0',textAlign:'center'}}>Drop a recording on the left to begin. 🐛</div>}
          {result && (
            <div className="rise">
              <div style={{fontFamily:'var(--display)',fontSize:30,color:'var(--ink)'}}>{result.name}</div>
              <div className="small" style={{color:'var(--leaf)',fontStyle:'italic',marginTop:2}}>spotted {result.early}</div>
              <div style={{marginTop:14,padding:'12px 14px',background:'rgba(199,214,189,0.4)',borderRadius:12}}>{result.hint}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============ Field ============ */
function ViewField({ profile, setProfile, t }){
  const items=[
    {emo:'☀️',title:'Bright and dry',body:'A good day to spray and harvest. Soil moisture is fine.',tone:'leaf'},
    {emo:'🌧',title:'Light rain at dusk',body:'About 2.4 mm expected. Open drainage on plot B.',tone:'warn'},
    {emo:'🦗',title:'Locusts 180 km west',body:"Wind shift in 48 h. We'll let you know if it gets closer.",tone:'alert'},
    {emo:'🌱',title:'Canopy looks healthy',body:'NDVI 0.71 — your crop is growing on schedule.',tone:'leaf'},
  ];
  const tone={leaf:'var(--leaf)',warn:'#A06B1F',alert:'var(--berry)'};
  return (
    <div className="view-fade">
      <Topbar crumb="Field Watch"/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">field</div>
          <h1 className="page-title">A <em>quiet daily check-in</em> for your land.</h1>
          <p className="page-lede">Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.</p>
        </div>
      </div>

      <LocationBar village={profile.village} setVillage={v=>setProfile({...profile,village:v})}
        state={profile.state} setState={s=>setProfile({...profile,state:s})}
        extra={<button className="btn primary" style={{padding:'8px 14px',fontSize:12}} onClick={()=>window.__catMood?.('excited',1500)}>🛰 Scan now</button>}/>

      <div className="grid-4" style={{marginBottom:18}}>
        {[['Temperature','29.4°C','feels 31'],['Humidity','64%','dewpt 22'],['Wind','12 km/h','NE'],['Rain · 24h','2.4 mm','prob 18%']].map(s=>(
          <div key={s[0]} className="card rise" style={{padding:'18px 20px'}}>
            <div className="page-eyebrow">{s[0]}</div>
            <div className="bignum" style={{fontSize:32,marginTop:6}}><em>{s[1]}</em></div>
            <div className="muted small" style={{marginTop:4}}>{s[2]}</div>
          </div>
        ))}
      </div>

      <div className="card rise rise-2">
        <div className="card-h"><h3>Today's notes</h3><span className="meta">last 24 hours · {profile.village}</span></div>
        <div style={{display:'flex',flexDirection:'column',gap:12}}>
          {items.map((i,k)=>(
            <div key={k} style={{display:'grid',gridTemplateColumns:'40px 180px 1fr',gap:14,alignItems:'center',padding:'12px 4px',borderBottom:'1px solid var(--line)'}}>
              <div style={{fontSize:24}}>{i.emo}</div>
              <div style={{fontFamily:'var(--display)',fontSize:18,color:tone[i.tone]}}>{i.title}</div>
              <div style={{color:'var(--ink-soft)',fontSize:14}}>{i.body}</div>
            </div>
          ))}
        </div>
      </div>
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

Object.assign(window, { Sidebar, TabBar, Topbar, LocationBar, ViewCrop, ViewDisease, ViewMarket, ViewIrrigation, ViewAcoustic, ViewField, VineBackdrop, mountCaterpillar });
