// ViewIrrigation — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

window.ViewIrrigation = ViewIrrigation;
