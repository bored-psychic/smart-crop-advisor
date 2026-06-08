// ViewIrrigation — real API wiring: city autofill + FAO backend + calamity tips
const { useState, useEffect, useRef, useCallback } = React;

const GROWTH_STAGES = ['Initial', 'Development', 'Mid-season', 'Late season'];

function ViewIrrigation({ profile, setProfile, t, fieldData, fieldLoading }){
  const [crop, setCrop]           = useState('Cotton');
  const [stage, setStage]         = useState('Mid-season');
  const [fieldArea, setFieldArea] = useState(2.0);
  const [lastRain, setLastRain]   = useState(0);
  const [temperature, setTemperature] = useState(32);
  const [humidity, setHumidity]   = useState(45);
  const [windSpeed, setWindSpeed] = useState(12);
  const [autofilling, setAutofilling] = useState(false);
  const [autofillNote, setAutofillNote] = useState('');
  const [calamityKey, setCalamityKey]   = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);
  const [result, setResult]       = useState(null);

  const autoRunRef = useRef(false);

  // Read prefetched weather from App (fetched on city change, before tab opens)
  useEffect(() => {
    setAutofilling(!!fieldLoading);
    const w = fieldData && fieldData.weather;
    if (!w) return;
    // Clamp autofilled weather to the slider/backend ranges so a gusty day
    // (e.g. wind > 50 km/h) can't push state past the schema caps → 422.
    const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
    if (w.temp     != null) setTemperature(clamp(parseFloat(w.temp), 10, 48));
    if (w.humidity != null) setHumidity(clamp(parseFloat(w.humidity), 10, 100));
    if (w.wind     != null) setWindSpeed(clamp(parseFloat(w.wind), 0, 50));
    if (w.rain_1h  != null) setLastRain(clamp(parseFloat(w.rain_1h) * 24, 0, 100));
    setAutofillNote(`Autofilled from ${fieldData.city || profile.village}`);
    const desc = (w.description || '').toLowerCase();
    const matched = Object.keys(CALAMITY_TIPS).find(k => desc.includes(k));
    setCalamityKey(matched || null);
    autoRunRef.current = true;
  }, [fieldData, fieldLoading]);

  // Auto-run calculation after autofill settles
  useEffect(() => {
    if (!autoRunRef.current) return;
    autoRunRef.current = false;
    const h = setTimeout(() => { handleSubmit(); }, 50);
    return () => clearTimeout(h);
  }, [temperature, humidity, windSpeed, lastRain]);

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
      <Topbar crumb={t('Watering')}/>
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('water')}</div>
          <h1 className="page-title">{t('Just enough water,')} <em>{t('just in time.')}</em></h1>
          <p className="page-lede">{t("We do the FAO water math behind the scenes and tell you simply: how many liters today, and when to water next.")}</p>
        </div>
      </div>

      <LocationBar
        t={t}
        village={profile.village} setVillage={v => setProfile({...profile, village: v})}
        state={profile.state}     setState={s  => setProfile({...profile, state: s})}
        extra={
          <>
            <select className="input" value={crop} onChange={e => setCrop(e.target.value)}>
              {CROP_KC_KEYS.map(c => <option key={c}>{c}</option>)}
            </select>
            {autofilling && <span style={{fontSize:12, color:'var(--ink-faint)', fontStyle:'italic'}}>{t('scanning…')}</span>}
            {autofillNote && !autofilling && <span style={{fontSize:12, color:'var(--leaf)', fontStyle:'italic'}}>{autofillNote}</span>}
          </>
        }
      />

      <div className="grid-2">
        {/* LEFT — Your field */}
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Your field')}</h3></div>

          {/* Growth stage tiles */}
          <div className="field">
            <div className="field-label"><span className="name">{t('Growth stage')}</span></div>
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
                >{t(s)}</button>
              ))}
            </div>
          </div>

          <Slider label={t('Field area')}   unit={t('ac')}   min={0.5} max={20}  step={0.1} value={fieldArea}   onChange={setFieldArea}/>
          <Slider label={t('Recent rain')}  unit={t('mm')}   min={0}   max={100}            value={lastRain}    onChange={setLastRain}/>
          <Slider label={t('Temperature')}  unit="°C"        min={10}  max={48}  step={0.5} value={temperature} onChange={setTemperature}/>
          <Slider label={t('Humidity')}     unit="%"         min={10}  max={100}            value={humidity}    onChange={setHumidity}/>
          <Slider label={t('Wind speed')}   unit={t('km/h')} min={0}   max={50}             value={windSpeed}   onChange={setWindSpeed}/>
        </div>

        {/* RIGHT — Get advice */}
        <div className="card rise rise-2">
          <div className="card-h"><h3>{t('Get advice')}</h3></div>
          <div style={{padding:'12px 0'}}>
            <button className="btn primary" onClick={handleSubmit} disabled={loading} style={{width:'100%'}}>
              {t('Calculate irrigation')}
            </button>
          </div>
          {loading && <Loading label={t('Calculating irrigation…')}/>}
          {error   && (
            <ErrorCard
              t={t}
              title={t('Could not calculate')}
              detail={!error.status ? t('No connection — check your network and try again.') : error.detail}
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
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>{t('Water needed')}</div>
              <div className="bignum">
                <em>{result.total_litres.toLocaleString()}</em>
                <span className="unit"> L</span>
              </div>
              <div style={{fontSize:13,color:'var(--ink-soft)',marginTop:4}}>{result.total_kl} kL</div>
            </div>

            <div className="card rise" style={{textAlign:'center'}}>
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>{t('Net irrigation')}</div>
              <div className="bignum">
                <em>{result.net_irrigation_mm}</em>
                <span className="unit"> {t('mm/day')}</span>
              </div>
            </div>

            <div className="card rise" style={{textAlign:'center'}}>
              <div style={{fontSize:11,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--ink-faint)',marginBottom:6}}>{t('Crop Kc factor')}</div>
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
              {t('urgency')} · {result.urgency}
            </div>
            <div style={{color:'var(--ink)',lineHeight:1.6}}>{result.advice}</div>
          </div>

          {/* Fertilizer card */}
          <div className="card rise" style={{background:'var(--leaf-soft)', borderColor:'var(--leaf)'}}>
            <div style={{fontSize:10,letterSpacing:'0.12em',textTransform:'uppercase',color:'var(--leaf)',marginBottom:8}}>
              {t('fertilizer')} · {result.fertilizer.growth_stage}
            </div>
            <div style={{color:'var(--ink)',marginBottom:6}}>
              <strong>{t('Nitrogen:')}</strong> {result.fertilizer.nitrogen}
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
              {t('weather tips')} · {calamityKey}
            </div>
            <ul style={{margin:0, paddingLeft:20, color:'var(--ink)', lineHeight:1.8}}>
              {CALAMITY_TIPS[calamityKey].map((tip, i) => (
                <li key={i}>{t(tip)}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

window.ViewIrrigation = ViewIrrigation;
