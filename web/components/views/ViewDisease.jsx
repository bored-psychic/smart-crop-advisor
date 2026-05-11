// ViewDisease — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

window.ViewDisease = ViewDisease;
