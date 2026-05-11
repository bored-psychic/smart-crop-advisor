// ViewAcoustic — single view
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

window.ViewAcoustic = ViewAcoustic;
