// ViewSoil — wired to /api/soil/analyze
const { useState } = React;

function SeverityBadge({ severity }) {
  const styles = {
    high:   { color: 'var(--berry)', background: 'rgba(232,112,95,0.14)' },
    medium: { color: 'var(--sun)',   background: 'rgba(240,192,96,0.14)' },
    low:    { color: 'var(--leaf)',  background: 'rgba(127,217,140,0.14)' },
  };
  const s = styles[severity] || styles.low;
  return (
    <span style={{ ...s, fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', padding: '2px 8px', borderRadius: 99 }}>
      {severity}
    </span>
  );
}

function ViewSoil({ profile, t }) {
  const [N, setN]   = useState(90);
  const [P, setP]   = useState(42);
  const [K, setK]   = useState(43);
  const [ph, setPh] = useState(6.5);
  const [om, setOm] = useState(1.2);
  const [targetCrop, setTargetCrop] = useState(profile.crop || '');
  const [areaAcres, setAreaAcres]   = useState(1.0);

  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);
  const { add: toast }        = useToast();

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await window.api.soilAnalyze({
        N, P, K, ph,
        organic_matter_pct: om,
        target_crop: targetCrop,
        area_acres: areaAcres,
      });
      setResult(data);
    } catch (err) {
      setError(err);
      toast('Analysis failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="view-fade">
      <Topbar crumb={t('Soil Health')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('soil health')}</div>
          <h1 className="page-title">{t('What does your')} <em>{t('soil need?')}</em></h1>
          <p className="page-lede">{t("Enter your soil test numbers. We'll find the gaps and tell you exactly what to apply.")}</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Soil Parameters')}</h3><span className="meta">npk · ph</span></div>
          <Slider label={t('Nitrogen')}   unit="kg/ha" min={0}   max={140} step={1}   value={N}  onChange={setN} />
          <Slider label={t('Phosphorus')} unit="kg/ha" min={5}   max={145} step={1}   value={P}  onChange={setP} />
          <Slider label={t('Potassium')}  unit="kg/ha" min={5}   max={205} step={1}   value={K}  onChange={setK} />
          <Slider label={t('Soil pH')}    unit=""      min={3.5} max={9.5} step={0.1} value={ph} onChange={setPh}
            hint={ph < 5.5 ? t('acidic') : ph < 7.5 ? t('sweet spot') : t('a touch alkaline')} />
        </div>
        <div className="card rise rise-2">
          <div className="card-h"><h3>{t('Field Details')}</h3><span className="meta">organic · crop · area</span></div>
          <Slider label={t('Organic Matter')} unit="%" min={0} max={20} step={0.1} value={om} onChange={setOm} />
          <div style={{ marginTop: 14 }}>
            <label style={{ fontSize: 13, color: 'var(--ink-soft)', display: 'block', marginBottom: 4 }}>{t('Target Crop')}</label>
            <input
              type="text"
              value={targetCrop}
              onChange={e => setTargetCrop(e.target.value)}
              placeholder={t('e.g. wheat')}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 10, border: '1px solid var(--glass-border)', background: 'var(--glass-bg)', color: 'var(--ink)', fontSize: 14, boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ marginTop: 14 }}>
            <label style={{ fontSize: 13, color: 'var(--ink-soft)', display: 'block', marginBottom: 4 }}>{t('Area (acres)')}</label>
            <input
              type="number"
              value={areaAcres}
              min={0.1}
              step={0.1}
              onChange={e => setAreaAcres(parseFloat(e.target.value) || 1)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: 10, border: '1px solid var(--glass-border)', background: 'var(--glass-bg)', color: 'var(--ink)', fontSize: 14, boxSizing: 'border-box' }}
            />
          </div>
        </div>
      </div>

      <button className="btn btn-full" onClick={handleSubmit} disabled={loading} style={{ marginTop: 18 }}>
        {loading ? t('Analysing…') : t('Analyse Soil')}
      </button>

      {loading && <Loading label={t('Analysing soil profile…')} />}

      {error && !loading && (
        <ErrorCard title={t('Could not analyse soil')} detail={error.detail} onRetry={handleSubmit} />
      )}

      {result && !loading && (
        <>
          <div className="card rise" style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <span className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('soil')} · {result.soil_type}</span>
            </div>
            <p style={{ fontStyle: 'italic', color: 'var(--ink-soft)', margin: 0 }}>{result.narrative}</p>
          </div>

          {result.deficiencies && result.deficiencies.length > 0 ? (
            <div className="card rise" style={{ marginTop: 14 }}>
              <div className="card-h"><h3>{t('Deficiencies')}</h3></div>
              {result.deficiencies.map((d, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: i < result.deficiencies.length - 1 ? '1px solid var(--glass-border)' : 'none' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontWeight: 600, textTransform: 'uppercase', fontSize: 15 }}>{d.nutrient}</span>
                    <SeverityBadge severity={d.severity} />
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--ink-soft)', textAlign: 'right' }}>
                    <span style={{ color: 'var(--ink)' }}>{d.current_value}</span>
                    <span style={{ margin: '0 4px' }}>vs</span>
                    <span>{d.optimal_min}–{d.optimal_max}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="card rise" style={{ marginTop: 14, color: 'var(--leaf)', fontWeight: 600 }}>
              ✓ {t('Soil looks healthy')}
            </div>
          )}

          {result.amendments && result.amendments.length > 0 && (
            <div className="card rise" style={{ marginTop: 14 }}>
              <div className="card-h"><h3>{t('Amendments')}</h3></div>
              {result.amendments.map((a, i) => (
                <div key={i} style={{ padding: '12px 0', borderBottom: i < result.amendments.length - 1 ? '1px solid var(--glass-border)' : 'none' }}>
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>{a.name}</div>
                  <div style={{ fontSize: 13, color: 'var(--ink-soft)', marginBottom: 2 }}>
                    {a.dose_kg_per_acre != null ? `${a.dose_kg_per_acre} kg/acre` : a.dose_tonnes_per_acre != null ? `${a.dose_tonnes_per_acre} t/acre` : ''}
                    {' · '}{a.application_method}
                  </div>
                  {a.notes && <div style={{ fontSize: 13, color: 'var(--ink-faint)', marginBottom: 2 }}>{a.notes}</div>}
                  <div style={{ fontSize: 12, color: 'var(--leaf)', marginTop: 4 }}>
                    {t('Effect in')} {a.time_to_effect_days} {t('days')}
                  </div>
                </div>
              ))}
            </div>
          )}

          {result.compatible_crops && result.compatible_crops.length > 0 && (
            <div className="card rise" style={{ marginTop: 14 }}>
              <div className="card-h"><h3>{t('Compatible Crops')}</h3></div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                {result.compatible_crops.map(crop => (
                  <span key={crop} style={{ padding: '5px 14px', borderRadius: 99, background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', fontSize: 13, textTransform: 'capitalize' }}>
                    {crop}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

window.ViewSoil = ViewSoil;
