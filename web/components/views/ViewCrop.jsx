// ViewCrop — wired to /api/crop/recommend + /api/soil/analyze
const { useState, useCallback, useEffect, useRef } = React;

function ProbBars({ probs, t }) {
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = sorted[0]?.[1] || 1;
  return (
    <div style={{ marginTop: 18 }}>
      <div className="page-eyebrow" style={{ marginBottom: 10 }}>{t('all crops')}</div>
      {sorted.map(([crop, prob]) => (
        <div key={crop} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{ width: 90, fontSize: 12, color: 'var(--ink-soft)', textAlign: 'right', textTransform: 'capitalize' }}>{crop}</div>
          <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.10)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${(prob / max) * 100}%`, height: '100%', background: 'var(--leaf)', borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ width: 36, fontSize: 12, color: 'var(--ink-faint)' }}>{Number(prob).toFixed(2)}%</div>
        </div>
      ))}
    </div>
  );
}

function ViewCrop({ profile, setProfile, t, areaAcres, setAreaAcres }) {
  const [N, setN] = useState(90);
  const [P, setP] = useState(42);
  const [K, setK] = useState(43);
  const [ph, setPh] = useState(6.5);
  const [temperature, setTemp] = useState(25);
  const [humidity, setHum] = useState(80);
  const [rainfall, setRain] = useState(200);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [soilResult, setSoilResult] = useState(null);
  const [wxNote, setWxNote] = useState('');
  const [wxLoading, setWxLoading] = useState(false);
  const wxDebounceRef = useRef(null);
  const wxLastCityRef = useRef('');

  useEffect(() => () => clearTimeout(wxDebounceRef.current), []);

  useEffect(() => {
    const val = (profile.village || '').trim();
    if (wxDebounceRef.current) clearTimeout(wxDebounceRef.current);
    if (val.length < 3 || val.toLowerCase() === wxLastCityRef.current) return;
    wxDebounceRef.current = setTimeout(async () => {
      setWxLoading(true);
      try {
        const data = await window.api.fieldWatchScan(val);
        const w = data && data.weather;
        if (w) {
          if (w.temp != null) setTemp(Math.min(45, Math.max(8, parseFloat(w.temp))));
          if (w.humidity != null) setHum(Math.min(100, Math.max(14, parseFloat(w.humidity))));
          const rf24 = (w.rain_1h != null ? parseFloat(w.rain_1h) : 0) * 24;
          if (rf24 > 0) setRain(Math.min(300, Math.max(20, rf24)));
          wxLastCityRef.current = val.toLowerCase();
          setWxNote(`Live weather · ${data.city || val}: ${w.temp?.toFixed(1)}°C, ${w.humidity}% humidity${w.description ? ' · ' + w.description : ''}`);
        } else {
          setWxNote(`No live weather for "${val}"`);
        }
      } catch (_) {
        setWxNote(`Couldn't fetch weather for "${val}"`);
      } finally {
        setWxLoading(false);
      }
    }, 500);
  }, [profile.village]);

  const handleSubmit = useCallback(() => {
    setLoading(true);
    setError(null);
    setSoilResult(null);

    const cropPromise = window.api.cropRecommend({ N, P, K, temperature, humidity, ph, rainfall });
    const soilPromise = window.api.soilAnalyze({
      N, P, K, ph,
      organic_matter_pct: 1.2,
      target_crop: profile.crop || undefined,
      area_acres: areaAcres,
    }).catch(() => null);

    Promise.all([cropPromise, soilPromise])
      .then(([cropData, soilData]) => {
        setResult(cropData);
        setSoilResult(soilData);
        setLoading(false);
      })
      .catch(e => {
        setError({
          status: e.status || null,
          detail: e.detail || e.message || String(e),
          message: e.message || String(e),
        });
        setLoading(false);
      });
  }, [N, P, K, temperature, humidity, ph, rainfall, areaAcres, profile.crop]);

  const handleReset = useCallback(() => {
    setN(90); setP(42); setK(43); setPh(6.5); setTemp(25); setHum(80); setRain(200);
    setAreaAcres(1.0);
    setResult(null); setError(null); setSoilResult(null);
  }, []);

  return (
    <div className="view-fade">
      <Topbar crumb={t('Crop Advisor')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('crop advisor')}</div>
          <h1 className="page-title">{t('Find what your soil')} <em>{t('wants to grow.')}</em></h1>
          <p className="page-lede">{t("Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.")}</p>
        </div>
      </div>

      <LocationBar
        t={t}
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state} setState={s => setProfile({ ...profile, state: s })}
        extra={<span className="tag">{t('🌦 kharif season')}</span>}
      />

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Soil')}</h3><span className="meta">{t('npk · ph')}</span></div>
          <Slider label={t('Nitrogen')} unit="kg/ha" min={0} max={140} value={N} onChange={setN}
            hint={N < 40 ? t('a little hungry') : N < 90 ? t('just right') : t('plenty')} />
          <Slider label={t('Phosphorus')} unit="kg/ha" min={5} max={145} value={P} onChange={setP} />
          <Slider label={t('Potassium')} unit="kg/ha" min={5} max={205} value={K} onChange={setK} />
          <Slider label={t('Soil pH')} unit="" min={3.5} max={9.5} step={0.1} value={ph} onChange={setPh}
            hint={ph < 5.5 ? t('acidic') : ph < 7.5 ? t('sweet spot') : t('a touch alkaline')} />
          <Slider label={t('Area')} unit="acres" min={0.5} max={50} step={0.5} value={areaAcres} onChange={setAreaAcres} />
        </div>
        <div className="card rise rise-2">
          <div className="card-h"><h3>{t('Weather')}</h3><span className="meta">{wxLoading ? t('fetching live…') : t('your local feel')}</span></div>
          {wxNote && (
            <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 10 }}>{wxNote}</div>
          )}
          <Slider label={t('Temperature')} unit="°C" min={8} max={45} step={0.5} value={temperature} onChange={setTemp} />
          <Slider label={t('Humidity')} unit="%" min={14} max={100} value={humidity} onChange={setHum} />
          <Slider label={t('Rainfall')} unit="mm" min={20} max={300} step={5} value={rainfall} onChange={setRain} />
          <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
            <button className="btn primary" onClick={handleSubmit} disabled={loading}>
              {loading ? t('🌿 Analyzing…') : t('🌱 Suggest a crop')}
            </button>
            <button className="btn ghost" onClick={handleReset}>{t('Reset')}</button>
          </div>
        </div>
      </div>

      {loading && <Loading label={t('Analyzing soil and climate…')} />}

      {error && !loading && (
        <ErrorCard
          t={t}
          title={error.status === 401 || error.status === 403
            ? t('API key misconfigured. Open web/config.js and verify the dev key.')
            : t('Could not analyze soil')}
          detail={!error.status && error.message ? t('No connection — check your network and try again.') : error.detail}
          onRetry={handleSubmit}
        />
      )}

      {result && !loading && (
        <div className="card rise" style={{ marginTop: 18 }}>
          <div className="grid-2" style={{ gridTemplateColumns: 'auto 1fr', alignItems: 'center', gap: 36 }}>
            <Donut value={result.top_crop.confidence} label="confidence" />
            <div>
              <div className="page-eyebrow">{t('our recommendation')}</div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 60, letterSpacing: '-0.02em', color: 'var(--ink)', marginTop: 4, lineHeight: 1.1 }}>
                {result.top_crop.emoji} <em style={{ color: 'var(--leaf)', fontStyle: 'italic', fontWeight: 300 }}>{result.top_crop.crop}</em>
              </div>
              {result.tip && (
                <p className="muted" style={{ maxWidth: 480, marginTop: 10 }}>{result.tip}</p>
              )}
              {result.soil && (
                <div style={{ marginTop: 14, padding: '12px 14px', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
                  <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('soil')} · {result.soil.soil_type}</div>
                  <div style={{ marginTop: 4, fontSize: 14 }}>{result.soil.indicator} {result.soil.advice}</div>
                </div>
              )}
              <div style={{ marginTop: 16 }}>
                <div className="page-eyebrow" style={{ marginBottom: 8 }}>{t('also great')}</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {result.alternatives.slice(0, 3).map(c => (
                    <div key={c.crop} className="tile" style={{ padding: '10px 14px' }}>
                      <span style={{ fontSize: 18, marginRight: 8 }}>{c.emoji}</span>
                      <span style={{ textTransform: 'capitalize' }}>{c.crop}</span>
                      <span style={{ color: 'var(--ink-faint)', marginLeft: 8, fontSize: 12 }}>{Number(c.confidence).toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          {result.all_probabilities && <ProbBars probs={result.all_probabilities} t={t} />}
        </div>
      )}

      {soilResult && !loading && (
        soilResult.deficiencies.length > 0 ? (
          <div className="card rise" style={{ marginTop: 14 }}>
            <div className="card-h">
              <h3>{t('Soil Deficiencies')}</h3>
              <span className="meta">{soilResult.soil_type}</span>
            </div>
            <p style={{ fontSize: 14, color: 'var(--ink-soft)', marginBottom: 14, fontStyle: 'italic' }}>
              {soilResult.narrative}
            </p>
            {soilResult.deficiencies.map(d => (
              <div key={d.nutrient} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 0', borderBottom: '1px solid var(--line)'
              }}>
                <span style={{ fontWeight: 500, textTransform: 'uppercase', fontSize: 13 }}>{d.nutrient}</span>
                <span style={{ fontSize: 12, color: 'var(--ink-faint)' }}>
                  {d.current_value} / optimal {d.optimal_min}–{d.optimal_max}
                </span>
                <span style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 99, fontWeight: 600,
                  background: d.severity === 'high' ? 'rgba(232,112,95,0.18)' : d.severity === 'medium' ? 'rgba(240,192,96,0.18)' : 'rgba(127,217,140,0.18)',
                  color: d.severity === 'high' ? 'var(--berry)' : d.severity === 'medium' ? 'var(--sun)' : 'var(--leaf)',
                }}>{d.severity}</span>
              </div>
            ))}
            {soilResult.amendments.length > 0 && (
              <div style={{ marginTop: 14 }}>
                <div className="page-eyebrow" style={{ marginBottom: 10 }}>{t('Amendments')}</div>
                {soilResult.amendments.map((a, i) => (
                  <div key={i} style={{ padding: '10px 0', borderBottom: '1px solid var(--line)' }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{a.name}
                      {a.dose_kg_per_acre && <span style={{ color: 'var(--ink-faint)', fontWeight: 400, marginLeft: 8, fontSize: 12 }}>{a.dose_kg_per_acre} kg/acre</span>}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--ink-soft)', marginTop: 3 }}>{a.application_method}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 2 }}>{a.notes} · {t('Effect in')} {a.time_to_effect_days} {t('days')}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="card rise" style={{ marginTop: 14, borderColor: 'rgba(127,217,140,0.32)', background: 'rgba(127,217,140,0.08)' }}>
            <span style={{ color: 'var(--leaf)', fontWeight: 600 }}>✓ {t('Soil looks healthy')}</span>
            <p style={{ fontSize: 14, color: 'var(--ink-soft)', marginTop: 6, fontStyle: 'italic' }}>{soilResult.narrative}</p>
          </div>
        )
      )}
    </div>
  );
}

window.ViewCrop = ViewCrop;
