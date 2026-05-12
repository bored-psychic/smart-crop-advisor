// ViewIrrigation — real API wiring: city autofill + FAO backend + calamity tips
const { useState, useEffect, useRef, useCallback } = React;

const GROWTH_STAGES = ['Initial', 'Development', 'Mid-season', 'Late season'];

function ViewIrrigation({ profile, setProfile, t }){
  const [crop, setCrop]           = useState('Cotton');
  const [stage, setStage]         = useState('Mid-season');
  const [fieldArea, setFieldArea] = useState(2.0);
  const [lastRain, setLastRain]   = useState(0);
  const [temperature, setTemperature] = useState(32);
  const [humidity, setHumidity]   = useState(45);
  const [windSpeed, setWindSpeed] = useState(12);
  const [city, setCity]           = useState('');
  const [autofilling, setAutofilling] = useState(false);
  const [autofillNote, setAutofillNote] = useState('');
  const [calamityKey, setCalamityKey]   = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [result, setResult]       = useState(null);

  // 400ms debounce for city → weather autofill
  const debounceRef = useRef(null);

  useEffect(() => {
    return () => clearTimeout(debounceRef.current);
  }, []);

  const handleCityChange = useCallback((val) => {
    setCity(val);
    setAutofillNote('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (val.trim().length > 2) {
      debounceRef.current = setTimeout(async () => {
        setAutofilling(true);
        try {
          const data = await window.api.fieldWatchScan(val.trim());
          const w = data.weather;
          if (w) {
            if (w.temp     != null) setTemperature(parseFloat(w.temp));
            if (w.humidity != null) setHumidity(parseFloat(w.humidity));
            if (w.wind     != null) setWindSpeed(parseFloat(w.wind));
            setAutofillNote(`Autofilled from ${val.trim()}`);
            // calamity detection
            const desc = (w.description || '').toLowerCase();
            const matched = Object.keys(CALAMITY_TIPS).find(k => desc.includes(k));
            setCalamityKey(matched || null);
          }
        } catch (_) {
          // silently ignore autofill errors
        } finally {
          setAutofilling(false);
        }
      }, 400);
    }
  }, []);

  async function handleSubmit(){
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await window.api.irrigationAdvise({
        crop,
        growth_stage: stage,
        field_area: fieldArea,
        last_rain_mm: lastRain,
        temperature,
        humidity,
        wind_speed: windSpeed,
      });
      setResult(data);
    } catch(err){
      setError({
        status: err.status || null,
        detail: err.detail || err.message || String(err),
        message: err.message || String(err),
      });
    } finally {
      setLoading(false);
    }
  }

  // Urgency color config
  const urgencyStyle = result ? (() => {
    if (result.urgency === 'urgent') return {
      bg: 'rgba(232,112,95,0.14)', border: 'var(--berry)'
    };
    if (result.urgency === 'light') return {
      bg: 'rgba(240,192,96,0.14)', border: 'var(--sun)'
    };
    return {
      bg: 'var(--leaf-soft)', border: 'var(--leaf)'
    };
  })() : null;

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

      <LocationBar
        village={profile.village} setVillage={v => setProfile({...profile, village: v})}
        state={profile.state}     setState={s  => setProfile({...profile, state: s})}
        extra={
          <select className="input" value={crop} onChange={e => setCrop(e.target.value)}>
            {CROP_KC_KEYS.map(c => <option key={c}>{c}</option>)}
          </select>
        }
      />

      <div className="grid-2">
        {/* LEFT — Your field */}
        <div className="card rise rise-1">
          <div className="card-h"><h3>Your field</h3></div>

          {/* City autofill */}
          <div className="field">
            <div className="field-label">
              <span className="name">City for weather autofill</span>
              {autofilling && <span style={{fontSize:12, color:'var(--ink-faint)', fontStyle:'italic', marginLeft:8}}>scanning…</span>}
            </div>
            <input
              className="input"
              type="text"
              placeholder="e.g. Nagpur"
              value={city}
              onChange={e => handleCityChange(e.target.value)}
              style={{width:'100%', marginBottom:4}}
            />
            {autofillNote && (
              <div style={{fontSize:12, color:'var(--leaf)', fontStyle:'italic'}}>{autofillNote}</div>
            )}
          </div>

          {/* Growth stage tiles */}
          <div className="field">
            <div className="field-label"><span className="name">Growth stage</span></div>
            <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8}}>
              {GROWTH_STAGES.map(s => (
                <button
                  key={s}
                  className={`tile${stage === s ? ' active' : ''}`}
                  style={{
                    padding:'10px 8px',
                    textAlign:'center',
                    fontSize:12,
                    ...(stage === s ? {background:'var(--leaf-soft)'} : {})
                  }}
                  onClick={() => setStage(s)}
                >{s}</button>
              ))}
            </div>
          </div>

          <Slider label="Field area"    unit="ac"   min={0.5} max={20}  step={0.1} value={fieldArea}   onChange={setFieldArea}/>
          <Slider label="Recent rain"   unit="mm"   min={0}   max={100}            value={lastRain}    onChange={setLastRain}/>
          <Slider label="Temperature"   unit="°C"   min={10}  max={48}  step={0.5} value={temperature} onChange={setTemperature}/>
          <Slider label="Humidity"      unit="%"    min={10}  max={100}            value={humidity}    onChange={setHumidity}/>
          <Slider label="Wind speed"    unit="km/h" min={0}   max={50}             value={windSpeed}   onChange={setWindSpeed}/>
        </div>

        {/* RIGHT — Get advice */}
        <div className="card rise rise-2">
          <div className="card-h"><h3>Get advice</h3></div>
          <div style={{padding:'12px 0'}}>
            <button className="btn primary" onClick={handleSubmit} disabled={loading} style={{width:'100%'}}>
              Calculate irrigation
            </button>
          </div>
          {loading && <Loading label="Calculating irrigation…"/>}
          {error   && (
            <ErrorCard
              title="Could not calculate"
              detail={!error.status ? 'No connection — check your network and try again.' : error.detail}
              onRetry={handleSubmit}
            />
          )}
        </div>
      </div>

      {/* Results */}
      {result && (
        <div style={{marginTop:24, display:'flex', flexDirection:'column', gap:20}}>

          {/* 3 metric tiles */}
          <div className="grid-3">
            <div className="card rise" style={{textAlign:'center'}}>
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>Water needed</div>
              <div className="bignum">
                <em>{result.total_litres.toLocaleString()}</em>
                <span className="unit"> L</span>
              </div>
              <div style={{fontSize:13,color:'var(--ink-soft)',marginTop:4}}>{result.total_kl} kL</div>
            </div>

            <div className="card rise" style={{textAlign:'center'}}>
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>Net irrigation</div>
              <div className="bignum">
                <em>{result.net_irrigation_mm}</em>
                <span className="unit"> mm/day</span>
              </div>
            </div>

            <div className="card rise" style={{textAlign:'center'}}>
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>Crop Kc factor</div>
              <div className="bignum"><em>{result.Kc}</em></div>
              <div style={{fontSize:13,color:'var(--ink-soft)',marginTop:4}}>{result.crop} · {stage}</div>
            </div>
          </div>

          {/* Urgency card */}
          <div className="card rise" style={{
            background: urgencyStyle.bg,
            borderColor: urgencyStyle.border,
          }}>
            <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:urgencyStyle.border,marginBottom:8}}>
              urgency · {result.urgency}
            </div>
            <div style={{color:'var(--ink)',lineHeight:1.6}}>{result.advice}</div>
          </div>

          {/* Fertilizer card */}
          <div className="card rise" style={{background:'var(--leaf-soft)', borderColor:'var(--leaf)'}}>
            <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--leaf)',marginBottom:8}}>
              fertilizer · {result.fertilizer.growth_stage}
            </div>
            <div style={{color:'var(--ink)',marginBottom:6}}>
              <strong>Nitrogen:</strong> {result.fertilizer.nitrogen}
            </div>
            <div style={{color:'var(--ink-soft)',fontSize:13,fontStyle:'italic'}}>{result.fertilizer.tip}</div>
          </div>

        </div>
      )}

      {/* Calamity tips — standalone, independent of result */}
      {calamityKey && CALAMITY_TIPS[calamityKey] && (
        <div style={{marginTop:24}}>
          <div className="card rise" style={{background:'rgba(240,192,96,0.14)', borderColor:'var(--sun)'}}>
            <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--sun)',marginBottom:8}}>
              weather tips · {calamityKey}
            </div>
            <ul style={{margin:0, paddingLeft:20, color:'var(--ink)', lineHeight:1.8}}>
              {CALAMITY_TIPS[calamityKey].map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

window.ViewIrrigation = ViewIrrigation;
