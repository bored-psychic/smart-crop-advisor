// ViewMarket — live price + forecast chart + sell advice
const { useState, useCallback } = React;

/* ---- SVG forecast chart ---- */
function ForecastChart({ forecast }) {
  if (!forecast || forecast.length < 2) {
    return (
      <div className="muted" style={{ padding: '20px', textAlign: 'center' }}>
        Not enough data to chart.
      </div>
    );
  }

  const W = 720, H = 200, pad = 30;
  const prices = forecast.map(d => d.price);
  const mins = forecast.map(d => d.min_price);
  const maxs = forecast.map(d => d.max_price);
  const allVals = [...prices, ...mins, ...maxs];
  const minV = Math.min(...allVals);
  const maxV = Math.max(...allVals);
  const rangeV = maxV - minV || 1;
  const n = forecast.length;

  const xp = i => pad + i * (W - pad * 2) / (n - 1);
  const yp = v => H - pad - ((v - minV) / rangeV) * (H - pad * 2);

  const bandTop = forecast.map((d, i) => `${i === 0 ? 'M' : 'L'}${xp(i)},${yp(d.max_price)}`).join(' ');
  const bandBot = [...forecast].reverse().map((d, i) => `L${xp(n - 1 - i)},${yp(d.min_price)}`).join(' ');
  const bandPath = bandTop + ' ' + bandBot + ' Z';

  const mainLine = forecast.map((d, i) => `${i === 0 ? 'M' : 'L'}${xp(i)},${yp(d.price)}`).join(' ');

  const gridYs = [0, 1, 2, 3].map(i => pad + i * (H - pad * 2) / 3);

  // Every 7th date label
  const dateLabels = forecast
    .map((d, i) => ({ i, date: d.date }))
    .filter(({ i }) => i % 7 === 0);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 200, display: 'block' }}>
      {gridYs.map((gy, i) => (
        <line key={i} x1={pad} y1={gy} x2={W - pad} y2={gy} stroke="rgba(255,255,255,0.08)" />
      ))}
      <path d={bandPath} fill="rgba(127,217,140,0.18)" />
      <path d={mainLine} fill="none" stroke="var(--leaf)" strokeWidth="2" strokeLinecap="round" />
      {dateLabels.map(({ i, date }) => (
        <text key={i} x={xp(i)} y={H - 4} textAnchor="middle"
          style={{ fontSize: 9, fill: 'var(--ink-faint)', fontFamily: 'var(--body)' }}>
          {(date ?? '').slice(5)}
        </text>
      ))}
    </svg>
  );
}

/* ---- Forecast table ---- */
const thStyle = { padding: '6px 8px', textAlign: 'left', color: 'var(--ink-soft)', fontWeight: 600 };
const tdStyle = { padding: '5px 8px', color: 'var(--ink)' };

function ForecastTable({ forecast }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
      <thead>
        <tr style={{ background: 'rgba(255,255,255,0.10)' }}>
          <th style={thStyle}>Date</th>
          <th style={thStyle}>Price</th>
          <th style={thStyle}>Min</th>
          <th style={thStyle}>Max</th>
        </tr>
      </thead>
      <tbody>
        {forecast.map((row, i) => (
          <tr key={row.date} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.05)' }}>
            <td style={tdStyle}>{row.date}</td>
            <td style={tdStyle}>₹{row.price.toFixed(0)}</td>
            <td style={tdStyle}>₹{row.min_price.toFixed(0)}</td>
            <td style={tdStyle}>₹{row.max_price.toFixed(0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ViewMarket({ profile, setProfile, t }) {
  const [crop, setCrop] = useState('Cotton');
  const [forecastDays, setForecastDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleSubmit = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await window.api.marketForecast(crop, profile.state, forecastDays);
      setResult(data);
    } catch (err) {
      setError({
        status: err.status,
        detail: err.detail || err.message || String(err),
        message: err.message
      });
    } finally {
      setLoading(false);
    }
  }, [crop, profile.state, forecastDays]);

  return (
    <div>
      <Topbar crumb="Market" />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">market</div>
          <h1 className="page-title">A <em>fair price,</em> a calm decision.</h1>
          <p className="page-lede">We watch the mandi prices and gently tell you whether to sell now or wait a couple of weeks. No charts to wrestle with.</p>
        </div>
      </div>

      <LocationBar
        village={profile.village}
        setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state}
        setState={s => setProfile({ ...profile, state: s })}
        extra={
          <select className="input" value={crop} onChange={e => setCrop(e.target.value)}>
            {ALL_CROPS.map(c => <option key={c}>{c}</option>)}
          </select>
        }
      />

      <div className="card rise rise-2" style={{ display: 'flex', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <Slider label="Forecast horizon" unit="days" min={7} max={60} value={forecastDays} onChange={setForecastDays} />
        </div>
        <button className="btn primary" onClick={handleSubmit} style={{ whiteSpace: 'nowrap', marginBottom: 2 }}>
          📊 Get forecast
        </button>
      </div>

      {loading && <Loading label="Fetching market data…" />}

      {error && !loading && (
        <ErrorCard
          title="Could not fetch forecast"
          detail={error.status === 401 || error.status === 403 ? 'API key issue — check your configuration.' : !error.status ? 'Network error — please check your connection.' : error.detail || 'Unexpected error.'}
          onRetry={handleSubmit}
        />
      )}

      {result && !loading && (
        <div className="view-fade">

          {/* 1. Live price card */}
          {result.live_price !== null ? (
            <div className="card rise rise-1">
              <div className="page-eyebrow">live mandi · {result.live_price.source}</div>
              <div className="bignum">₹<em>{result.live_price.today_price?.toFixed(0) ?? '—'}</em><span className="unit">/q</span></div>
              <div className="small muted" style={{ marginTop: 4 }}>
                {result.live_price.mandis_checked} mandis · state factor {result.live_price.state_factor?.toFixed(2) ?? '—'}
              </div>
              <div style={{ marginTop: 8 }}>
                {result.live_price.live
                  ? <span className="tag" style={{ background: 'var(--leaf-soft)', color: 'var(--leaf)' }}>🟢 LIVE</span>
                  : <span className="tag warn">🟡 ESTIMATED</span>
                }
              </div>
            </div>
          ) : (
            <div className="card rise rise-1" style={{ color: 'var(--ink-soft)', fontStyle: 'italic' }}>
              Live mandi data not available — showing model forecast only.
            </div>
          )}

          {/* 2. Three metric tiles */}
          <div className="card rise rise-2">
            <div className="grid-3">
              <div>
                <div className="page-eyebrow">best price</div>
                <div className="bignum">₹<em>{result.best_price?.toFixed(0) ?? '—'}</em><span className="unit">/q</span></div>
                <div className="small muted" style={{ marginTop: 4 }}>on {result.best_date}</div>
              </div>
              <div>
                <div className="page-eyebrow">worst price</div>
                <div className="bignum">₹<em>{result.worst_price?.toFixed(0) ?? '—'}</em><span className="unit">/q</span></div>
                <div className="small muted" style={{ marginTop: 4 }}>on {result.worst_date}</div>
              </div>
              <div>
                <div className="page-eyebrow">average price</div>
                <div className="bignum">₹<em>{result.avg_price?.toFixed(0) ?? '—'}</em><span className="unit">/q</span></div>
                <div className="small muted" style={{ marginTop: 4 }}>over {forecastDays} days</div>
              </div>
            </div>
          </div>

          {/* 3. Sell advice card */}
          <div className="card rise rise-3" style={{ background: 'rgba(240,192,96,0.12)', borderColor: 'rgba(240,192,96,0.32)' }}>
            <div className="page-eyebrow">our advice</div>
            <div style={{ fontSize: 15, color: 'var(--ink)', lineHeight: 1.6, marginTop: 6 }}>{result.sell_advice}</div>
          </div>

          {/* 4. SVG forecast chart */}
          <div className="card rise rise-4">
            <div className="card-h" style={{ marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>Price forecast · {result.crop}</h3>
              <span className="tag">📍 {result.state}</span>
            </div>
            <ForecastChart forecast={result.forecast} />
          </div>

          {/* 5. Full forecast table expander */}
          {result.forecast && result.forecast.length > 0 && (
            <div className="card rise rise-5">
              <details>
                <summary style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--ink-soft)', userSelect: 'none', padding: '4px 0' }}>
                  Full forecast table ({result.forecast.length} days)
                </summary>
                <div style={{ marginTop: 12, overflowX: 'auto' }}>
                  <ForecastTable forecast={result.forecast} />
                </div>
              </details>
            </div>
          )}

        </div>
      )}
    </div>
  );
}

window.ViewMarket = ViewMarket;
