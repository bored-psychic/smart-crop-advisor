// ViewCrop — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

window.ViewCrop = ViewCrop;
