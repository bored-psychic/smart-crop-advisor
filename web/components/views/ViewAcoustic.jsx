// ViewAcoustic — pre-check gate (Task 5.1) + rich result rendering (Task 5.2)
const { useState, useEffect, useRef, useMemo, useCallback } = React;

const BAR_COUNT = window.innerWidth <= 640 ? 28 : 40;

/* ===== Module-scope helpers ===== */

function roleColor(role){
  if(role==='pest')       return 'var(--berry)';
  if(role==='pollinator') return 'var(--leaf)';
  if(role==='vector')     return '#A06B1F';
  return 'var(--ink-faint)';
}

function MethodBadge({ method }){
  if(!method) return null;
  const goodMethods = ['yamnet','claude_vision','gemini_audio'];
  const color = goodMethods.includes(method) ? 'var(--leaf)' : 'var(--berry)';
  return (
    <span style={{
      display:'inline-block',fontSize:11,fontWeight:600,letterSpacing:'0.08em',
      textTransform:'uppercase',padding:'3px 9px',borderRadius:999,
      background:color,color:'#fff',marginBottom:12
    }}>{method.replace(/_/g,' ')}</span>
  );
}

function TopBars({ top3 }){
  if(!top3||!top3.length) return null;
  const maxVal = Math.max(...top3.map(([,p])=>p), 1);
  return (
    <div style={{marginTop:16}}>
      <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:8}}>top detections</div>
      {top3.map(([name,pct],i)=>(
        <div key={i} style={{marginBottom:8}}>
          <div style={{display:'flex',justifyContent:'space-between',fontSize:13,marginBottom:3}}>
            <span>{name}</span><span style={{color:'var(--ink-soft)'}}>{Math.round(pct)}%</span>
          </div>
          <div style={{height:8,borderRadius:4,background:'rgba(42,51,40,0.08)',overflow:'hidden'}}>
            <div style={{height:'100%',width:`${(pct/maxVal)*100}%`,background:'var(--leaf)',borderRadius:4,transition:'width 0.8s ease'}}/>
          </div>
        </div>
      ))}
    </div>
  );
}

function BandChart({ bandEnergy }){
  if(!bandEnergy||!Object.keys(bandEnergy).length) return null;
  const entries = Object.entries(bandEnergy);
  const maxVal  = Math.max(...entries.map(([,v])=>v), 0.001);
  return (
    <div style={{marginTop:20}}>
      <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:8}}>band energy</div>
      {entries.map(([band,val],i)=>(
        <div key={i} style={{marginBottom:7}}>
          <div style={{display:'flex',justifyContent:'space-between',fontSize:12,marginBottom:2}}>
            <span style={{color:'var(--ink-soft)'}}>{band}</span>
            <span style={{color:'var(--ink-faint)'}}>{val.toFixed ? val.toFixed(4) : val}</span>
          </div>
          <div style={{height:7,borderRadius:4,background:'rgba(42,51,40,0.08)',overflow:'hidden'}}>
            <div style={{height:'100%',width:`${(val/maxVal)*100}%`,background:'var(--leaf)',borderRadius:4}}/>
          </div>
        </div>
      ))}
    </div>
  );
}

function RichResult({ r }){
  const rc = roleColor(r.role);
  return (
    <div className="rise">
      {/* Method badge */}
      <MethodBadge method={r.analysis_method}/>

      {/* Pest card */}
      <div style={{
        padding:'16px 18px',borderRadius:14,marginBottom:14,
        border:`2px solid ${rc}`,
        background: r.role==='pest'?'rgba(182,85,58,0.06)':r.role==='pollinator'?'rgba(130,176,130,0.10)':'rgba(42,51,40,0.04)'
      }}>
        <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:6}}>
          <span style={{fontSize:36}}>{r.icon || '🐛'}</span>
          <div style={{fontFamily:'var(--display)',fontSize:32,color:rc,lineHeight:1}}>{r.pest}</div>
        </div>
        <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:10}}>
          <span style={{
            fontSize:11,fontWeight:600,letterSpacing:'0.08em',textTransform:'uppercase',
            padding:'3px 9px',borderRadius:999,background:rc,color:'#fff'
          }}>{r.role}</span>
          {r.severity && (
            <span style={{
              fontSize:11,fontWeight:600,letterSpacing:'0.08em',textTransform:'uppercase',
              padding:'3px 9px',borderRadius:999,
              background:'rgba(42,51,40,0.08)',color:'var(--ink-soft)'
            }}>{r.severity}</span>
          )}
        </div>
        {r.action && (
          <div style={{
            padding:'10px 13px',borderRadius:10,fontSize:14,lineHeight:1.5,
            background: r.role==='pollinator'?'rgba(130,176,130,0.2)':'rgba(199,214,189,0.4)',
            color: r.role==='ambient'||r.is_pest===false?'var(--ink-soft)':'var(--ink)'
          }}>{r.action}</div>
        )}
      </div>

      {/* 4-metric grid */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:10,marginBottom:14}}>
        {[
          {label:'Confidence', value:`${Math.round(r.confidence||0)}%`},
          {label:'Duration',   value:`${r.analyzed_seconds||0}s / ${r.duration_seconds||0}s`},
          {label:'Sample rate',value:`${r.sample_rate||0} Hz`},
          {label:'Energy',     value:r.energy_level||'—'},
        ].map(({label,value})=>(
          <div key={label} style={{
            padding:'10px 12px',borderRadius:12,background:'rgba(199,214,189,0.3)',textAlign:'center'
          }}>
            <div style={{fontSize:16,fontWeight:700,color:'var(--ink)',fontFamily:'var(--display)'}}>{value}</div>
            <div style={{fontSize:10,letterSpacing:'0.1em',textTransform:'uppercase',color:'var(--ink-faint)',marginTop:3}}>{label}</div>
          </div>
        ))}
      </div>

      {/* Top-3 bars */}
      <TopBars top3={r.top3}/>

      {/* Claude advice */}
      {r.claude_advice && (
        <div style={{
          marginTop:16,padding:'12px 16px',borderRadius:12,
          background:'rgba(130,176,130,0.15)',borderLeft:'3px solid var(--leaf)',
          fontSize:14,lineHeight:1.6,color:'var(--ink)'
        }}>
          <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--leaf)',marginBottom:6,fontWeight:600}}>Claude advice</div>
          {r.claude_advice}
        </div>
      )}

      {/* Quality warnings from result */}
      {r.quality_warnings && r.quality_warnings.length > 0 && (
        <div style={{
          marginTop:14,padding:'10px 14px',borderRadius:12,
          background:'rgba(160,107,31,0.08)',border:'1px solid rgba(160,107,31,0.3)'
        }}>
          <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:'#A06B1F',marginBottom:6,fontWeight:600}}>quality notes</div>
          {r.quality_warnings.map((w,i)=>(
            <div key={i} style={{fontSize:13,color:'#A06B1F',marginBottom:3}}>
              {window.ACOUSTIC_WARNING_LABELS?.[w] || w}
            </div>
          ))}
        </div>
      )}

      {/* Band energy chart */}
      <BandChart bandEnergy={r.band_energy}/>

      {/* Methodology note */}
      {r.methodology_note && (
        <div style={{marginTop:14,fontSize:12,color:'var(--ink-faint)',fontStyle:'italic',lineHeight:1.5}}>
          {r.methodology_note}
        </div>
      )}

      {/* Reference library expander */}
      <details style={{marginTop:18}}>
        <summary style={{cursor:'pointer',fontSize:13,color:'var(--ink-soft)',userSelect:'none'}}>
          Reference library ({Object.keys(window.PEST_META||{}).length} known insects)
        </summary>
        <div style={{marginTop:10,overflowX:'auto'}}>
          <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
            <thead>
              <tr style={{borderBottom:'1px solid var(--line-2)'}}>
                {['Icon','Name','Role','Severity','Freq range'].map(h=>(
                  <th key={h} style={{textAlign:'left',padding:'4px 8px',color:'var(--ink-faint)',fontWeight:600,letterSpacing:'0.06em',textTransform:'uppercase',fontSize:10}}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(window.PEST_META||{}).map(([name,meta])=>(
                <tr key={name} style={{borderBottom:'1px solid rgba(42,51,40,0.06)'}}>
                  <td style={{padding:'5px 8px',fontSize:18}}>{meta.icon}</td>
                  <td style={{padding:'5px 8px'}}>{name}</td>
                  <td style={{padding:'5px 8px',color:roleColor(meta.role)}}>{meta.roleLabel}</td>
                  <td style={{padding:'5px 8px',color:'var(--ink-soft)',textTransform:'capitalize'}}>{meta.severity}</td>
                  <td style={{padding:'5px 8px',color:'var(--ink-faint)'}}>
                    {(r.pest===name && r.freq_range) ? r.freq_range : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

/* ===== Main component ===== */

function ViewAcoustic({ profile, t }){
  const [file, setFile]                       = useState(null);
  const [preCheckWarnings, setPreCheckWarnings] = useState([]);
  const [preCheckError, setPreCheckError]     = useState(null);
  const [loading, setLoading]                 = useState(false);
  const [error, setError]                     = useState(null);
  const [result, setResult]                   = useState(null);
  const [cropType, setCropType]               = useState('Unknown');
  const [drag, setDrag]                       = useState(false);
  const [bars, setBars]                       = useState(Array(BAR_COUNT).fill(0.1));
  const inputRef = useRef();

  // Animate bars while loading
  useEffect(()=>{
    if(loading){
      const id = setInterval(()=>setBars(Array.from({length:BAR_COUNT},()=>0.2+Math.random()*0.7)),100);
      return ()=>clearInterval(id);
    } else {
      setBars(Array(BAR_COUNT).fill(0.1));
    }
  },[loading]);

  // Object URL — create once per file, revoke on change/unmount
  const audioUrl = useMemo(()=>{
    if(!file) return null;
    return URL.createObjectURL(file);
  },[file]);
  useEffect(()=>{
    return ()=>{ if(audioUrl) URL.revokeObjectURL(audioUrl); };
  },[audioUrl]);

  // Pre-check: size + AudioContext decode
  async function runPreCheck(f){
    setPreCheckWarnings([]);
    setPreCheckError(null);
    setResult(null);
    setError(null);

    // 1. Size gate (hard block)
    if(f.size > 20 * 1024 * 1024){
      setPreCheckError('File too large (max 20 MB)');
      return;
    }

    // 2. AudioContext decode (advisory warnings only)
    try {
      const arrayBuf = await f.arrayBuffer();
      const Ctx = window.AudioContext || window.webkitAudioContext;
      const ctx = new Ctx();
      const buf = await ctx.decodeAudioData(arrayBuf);
      ctx.close();

      const duration   = buf.duration;
      const sampleRate = buf.sampleRate;
      const samples    = buf.getChannelData(0);
      const rms        = Math.sqrt(samples.reduce((s,v)=>s+v*v,0)/samples.length);

      const warns = [];
      if(duration < 3)       warns.push('too_short');
      if(rms < 0.002)        warns.push('below_noise_floor');
      if(sampleRate < 8000)  warns.push('low_sample_rate');
      setPreCheckWarnings(warns);
    } catch(_){
      // Unsupported format — advisory only, allow submit
      setPreCheckError("Cannot preview this audio format — upload anyway to let the server analyze it.");
    }
  }

  function handleFile(f){
    if(!f) return;
    setFile(f);
    runPreCheck(f);
  }

  function onDrop(e){
    e.preventDefault();
    setDrag(false);
    handleFile(e.dataTransfer.files[0]);
  }

  function clearAll(){
    setFile(null);
    setPreCheckWarnings([]);
    setPreCheckError(null);
    setResult(null);
    setError(null);
    setLoading(false);
  }

  // Normalize error
  function normalizeError(err){
    if(!err) return {status:null, detail:'Unknown error', message:'Unknown error'};
    const status  = err.status || null;
    const detail  = err.detail || err.message || String(err);
    let message;
    if(status===401||status===403) message = 'Invalid or missing API key.';
    else if(!status)               message = 'Network error — check your connection.';
    else                           message = detail;
    return {status, detail, message};
  }

  async function analyze(){
    if(!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    window.__catMood?.('thinking', 3000);
    try {
      const res = await window.api.acousticAnalyze(file, cropType || 'Unknown');
      setResult(res);
      window.__catMood?.('excited', 1200);
    } catch(err){
      setError(normalizeError(err));
    } finally {
      setLoading(false);
    }
  }

  // Analyze button disabled: loading OR size-hard-block only
  const isSizeBlock = preCheckError && preCheckError.startsWith('File too large');
  const analyzeDisabled = loading || isSizeBlock || !file;

  /* ===== Main render ===== */
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
        {/* LEFT: Upload card */}
        <div className="card rise rise-1">
          <div className="card-h"><h3>Upload a recording</h3><span className="tag">~6 seconds</span></div>

          {/* Crop type input */}
          <input
            className="input"
            placeholder="Crop type (optional)"
            value={cropType}
            onChange={e=>setCropType(e.target.value)}
            style={{marginBottom:12,width:'100%'}}
          />

          {/* Drag-drop zone */}
          <div className="drop"
            onClick={()=>inputRef.current?.click()}
            onDragOver={e=>{e.preventDefault();setDrag(true)}}
            onDragLeave={()=>setDrag(false)}
            onDrop={onDrop}
            style={{
              borderColor:drag?'var(--leaf)':'var(--line-2)',
              background:drag?'rgba(199,214,189,0.4)':'rgba(255,255,255,0.4)'
            }}>
            <div style={{fontSize:36}}>{file?'🎵':'🎙'}</div>
            <div style={{marginTop:10,fontSize:14}}>
              {file ? <strong>{file.name}</strong> : <strong>Drag &amp; drop your field audio here</strong>}
            </div>
            <div className="muted small" style={{marginTop:4}}>
              {file
                ? `${(file.size/1024).toFixed(0)} KB · ready`
                : 'or click to choose · wav · mp3 · m4a · ogg · webm'}
            </div>
            <input ref={inputRef} type="file" accept="audio/*" style={{display:'none'}}
              onChange={e=>handleFile(e.target.files[0])}/>
          </div>

          {/* Audio preview */}
          {file && audioUrl && (
            <audio controls src={audioUrl} style={{width:'100%',marginTop:12,borderRadius:10}}/>
          )}

          {/* Pre-check warnings (advisory, yellow) */}
          {preCheckWarnings.length > 0 && (
            <div style={{
              marginTop:12,padding:'10px 14px',borderRadius:12,
              background:'rgba(160,107,31,0.08)',border:'1px solid rgba(160,107,31,0.3)'
            }}>
              {preCheckWarnings.map((w,i)=>(
                <div key={i} style={{fontSize:13,color:'#A06B1F',marginBottom:i<preCheckWarnings.length-1?4:0}}>
                  {window.ACOUSTIC_WARNING_LABELS?.[w] || w}
                </div>
              ))}
            </div>
          )}

          {/* Pre-check error (hard or format note) */}
          {preCheckError && (
            <div style={{
              marginTop:12,padding:'10px 14px',borderRadius:12,fontSize:13,
              border:`1px solid var(--berry)`,background:'rgba(182,85,58,0.06)',
              color:'var(--berry)'
            }}>{preCheckError}</div>
          )}

          {/* Action row */}
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginTop:14,gap:10}}>
            <div className="muted small" style={{fontStyle:'italic'}}>tip: 15–30 cm from the stem · breathe slowly</div>
            <div style={{display:'flex',gap:8}}>
              <button className="btn" onClick={clearAll}>clear</button>
              <button className="btn primary" onClick={analyze} disabled={analyzeDisabled}>
                {loading ? '🎧 listening…' : '🔊 analyze'}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT: Result card */}
        <div className="card rise rise-2">
          <div className="card-h">
            <h3>What we heard</h3>
            {result && <span className="tag alert">{result.severity}</span>}
          </div>

          {/* Waveform bars */}
          <div style={{display:'flex',justifyContent:'center',alignItems:'flex-end',gap:3,height:120,padding:'10px 0'}}>
            {bars.map((b,i)=>(
              <div key={i} style={{
                width:5,height:`${Math.max(8,b*100)}%`,
                background:'var(--leaf-2)',borderRadius:2,
                transition:'height .12s ease',
                opacity:loading?0.9:result?0.6:0.3
              }}/>
            ))}
          </div>

          {/* Loading */}
          {loading && <Loading label="Listening to your field…"/>}

          {/* Error */}
          {error && !loading && (
            <ErrorCard
              title="Analysis failed"
              detail={error.message}
              onRetry={analyze}
            />
          )}

          {/* Idle hint */}
          {!result && !loading && !error && (
            <div className="muted" style={{padding:'10px 0',textAlign:'center'}}>Drop a recording on the left to begin. 🐛</div>
          )}

          {/* Rich result */}
          {result && !loading && <RichResult r={result}/>}
        </div>
      </div>
    </div>
  );
}

window.ViewAcoustic = ViewAcoustic;
