// ViewCrop — wired to /api/crop/recommend
const { useState, useCallback } = React;

function ProbBars({ probs }) {
  const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]).slice(0, 8);
  const max = sorted[0]?.[1] || 1;
  return (
    <div style={{ marginTop: 18 }}>
      <div className="page-eyebrow" style={{ marginBottom: 10 }}>all crops</div>
      {sorted.map(([crop, prob]) => (
        <div key={crop} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{ width: 90, fontSize: 12, color: 'var(--ink-soft)', textAlign: 'right', textTransform: 'capitalize' }}>{crop}</div>
          <div style={{ flex: 1, height: 6, background: 'rgba(42,51,40,0.08)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${(prob / max) * 100}%`, height: '100%', background: 'var(--leaf)', borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ width: 36, fontSize: 12, color: 'var(--ink-faint)' }}>{(prob * 100).toFixed(0)}%</div>
        </div>
      ))}
    </div>
  );
}

function ViewCrop({ profile, setProfile, t }) {
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

  const handleSubmit = useCallback(() => {
    setLoading(true);
    setError(null);
    window.__catMood?.('thinking', 2500);
    window.api.cropRecommend({ N, P, K, temperature, humidity, ph, rainfall })
      .then(r => {
        setResult(r);
        setLoading(false);
        window.__catMood?.('excited', 1500);
      })
      .catch(e => {
        setError(e);
        setLoading(false);
      });
  }, [N, P, K, temperature, humidity, ph, rainfall]);

  const handleReset = useCallback(() => {
    setN(90); setP(42); setK(43); setPh(6.5); setTemp(25); setHum(80); setRain(200);
    setResult(null); setError(null);
  }, []);

  return (
    <div className="view-fade">
      <Topbar crumb="Crop Advisor" />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">crop advisor</div>
          <h1 className="page-title">Find what your soil <em>wants to grow.</em></h1>
          <p className="page-lede">Tell us a little about your field. We'll quietly look through 26 crops and suggest the one your land will love most.</p>
        </div>
      </div>

      <LocationBar
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state} setState={s => setProfile({ ...profile, state: s })}
        extra={<span className="tag">🌦 kharif season</span>}
      />

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>Soil</h3><span className="meta">npk · ph</span></div>
          <Slider label="Nitrogen" unit="kg/ha" min={0} max={140} value={N} onChange={setN}
            hint={N < 40 ? 'a little hungry' : N < 90 ? 'just right' : 'plenty'} />
          <Slider label="Phosphorus" unit="kg/ha" min={5} max={145} value={P} onChange={setP} />
          <Slider label="Potassium" unit="kg/ha" min={5} max={205} value={K} onChange={setK} />
          <Slider label="Soil pH" unit="" min={3.5} max={9.5} step={0.1} value={ph} onChange={setPh}
            hint={ph < 5.5 ? 'acidic' : ph < 7.5 ? 'sweet spot' : 'a touch alkaline'} />
        </div>
        <div className="card rise rise-2">
          <div className="card-h"><h3>Weather</h3><span className="meta">your local feel</span></div>
          <Slider label="Temperature" unit="°C" min={8} max={45} step={0.5} value={temperature} onChange={setTemp} />
          <Slider label="Humidity" unit="%" min={14} max={100} value={humidity} onChange={setHum} />
          <Slider label="Rainfall" unit="mm" min={20} max={300} step={5} value={rainfall} onChange={setRain} />
          <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
            <button className="btn primary" onClick={handleSubmit} disabled={loading}>
              {loading ? '🌿 Analyzing…' : '🌱 Suggest a crop'}
            </button>
            <button className="btn ghost" onClick={handleReset}>Reset</button>
          </div>
        </div>
      </div>

      {loading && <Loading label="Analyzing soil and climate…" />}

      {error && !loading && (
        <ErrorCard
          title={error.status === 401 || error.status === 403
            ? 'API key misconfigured. Open web/config.js and verify the dev key.'
            : 'Could not analyze soil'}
          detail={!error.status && error.message ? 'No connection — check your network and try again.' : error.detail}
          onRetry={handleSubmit}
        />
      )}

      {result && !loading && (
        <div className="card rise" style={{ marginTop: 18 }}>
          <div className="grid-2" style={{ gridTemplateColumns: 'auto 1fr', alignItems: 'center', gap: 36 }}>
            <Donut value={result.top_crop.confidence * 100} label="confidence" />
            <div>
              <div className="page-eyebrow">our recommendation</div>
              <div style={{ fontFamily: 'var(--display)', fontSize: 60, letterSpacing: '-0.02em', color: 'var(--ink)', marginTop: 4, lineHeight: 1.1 }}>
                {result.top_crop.emoji} <em style={{ color: 'var(--leaf)', fontStyle: 'italic', fontWeight: 300 }}>{result.top_crop.crop}</em>
              </div>
              {result.tip && (
                <p className="muted" style={{ maxWidth: 480, marginTop: 10 }}>{result.tip}</p>
              )}
              {result.soil && (
                <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(199,214,189,0.4)', borderRadius: 12 }}>
                  <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>soil · {result.soil.soil_type}</div>
                  <div style={{ marginTop: 4, fontSize: 14 }}>{result.soil.indicator} {result.soil.advice}</div>
                </div>
              )}
              <div style={{ marginTop: 16 }}>
                <div className="page-eyebrow" style={{ marginBottom: 8 }}>also great</div>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  {result.alternatives.slice(0, 3).map(c => (
                    <div key={c.crop} className="tile" style={{ padding: '10px 14px' }}>
                      <span style={{ fontSize: 18, marginRight: 8 }}>{c.emoji}</span>
                      <span style={{ textTransform: 'capitalize' }}>{c.crop}</span>
                      <span style={{ color: 'var(--ink-faint)', marginLeft: 8, fontSize: 12 }}>{(c.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          {result.all_probabilities && <ProbBars probs={result.all_probabilities} />}
        </div>
      )}
    </div>
  );
}

window.ViewCrop = ViewCrop;
