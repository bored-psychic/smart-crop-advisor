// garden.jsx — View components only (atoms/sidebar/caterpillar live in atoms.jsx)
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

Object.assign(window, { ViewCrop, ViewDisease, ViewMarket, ViewIrrigation, ViewAcoustic, ViewField });
