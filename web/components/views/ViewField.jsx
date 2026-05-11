// ViewField — live field-watch scan: weather, flood, fire, locust, AQI + helplines + WhatsApp builder
const { useState, useEffect, useCallback } = React;

function ViewField({ profile, setProfile, t }) {
  const [city, setCity]       = useState(profile.village || '');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);
  const { toasts, add: addToast } = useToast();

  const doScan = useCallback(async (scanCity) => {
    const target = (scanCity || city).trim();
    if (!target) return;
    setLoading(true);
    setError(null);
    try {
      const data = await window.api.fieldWatchScan(target);
      setResult(data);
    } catch (err) {
      let errObj = { status: err.status || 0, detail: '', message: err.message || 'Unknown error' };
      if (err.status === 401 || err.status === 403) {
        errObj.detail = 'Authentication error. Please refresh and try again.';
      } else if (!navigator.onLine) {
        errObj.detail = 'No internet connection. Check your network and retry.';
      } else {
        errObj.detail = err.detail || err.message || 'Could not reach server.';
      }
      setError(errObj);
    } finally {
      setLoading(false);
    }
  }, [city]);

  // Auto-scan on mount if city is pre-filled
  useEffect(() => {
    if ((profile.village || '').trim().length > 0) {
      doScan(profile.village.trim());
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ---- Risk badge helpers ---- */
  const riskStyle = (risk) => {
    if (risk === 'HIGH')   return { bg: 'rgba(182,85,58,0.08)',   border: 'var(--berry)', color: 'var(--berry)',   icon: '🔴' };
    if (risk === 'MEDIUM') return { bg: 'rgba(160,107,31,0.08)',  border: '#A06B1F',      color: '#A06B1F',        icon: '🟡' };
    return                        { bg: 'rgba(62,107,62,0.08)',   border: 'var(--leaf)',  color: 'var(--leaf)',    icon: '🟢' };
  };

  /* ---- WhatsApp message ---- */
  const waMessage = result ? [
    '🌾 KisanOS Field Report',
    `Farmer: ${profile.name || 'Farmer'} | ${profile.village || result.city}`,
    `Crop: ${profile.crop || 'General'}`,
    `Location: ${result.city}`,
    `Risk: ${result.overall_risk}`,
    result.weather
      ? `Weather: ${result.weather.temp?.toFixed(1)}°C, ${result.weather.humidity}% humidity, ${result.weather.wind?.toFixed(0)} km/h wind`
      : '',
    result.weather?.description || '',
    result.flood  ? `Flood risk: ${result.flood.flood_risk}` : '',
    result.fire?.risk !== 'NONE' ? `Fire: ${result.fire.hotspots_nearby} hotspots (${result.fire.risk})` : '',
    'Sent via KisanOS',
  ].filter(Boolean).join('\n') : '';

  /* ---- Alert card helper ---- */
  function AlertCard({ title, risk, children }) {
    const s = riskStyle(risk);
    return (
      <div className="card rise" style={{ borderColor: s.border, background: s.bg }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
          <span style={{ fontSize: 18 }}>{s.icon}</span>
          <span style={{ fontFamily: 'var(--display)', fontSize: 16, color: s.color }}>{title}</span>
          <span style={{
            marginLeft: 'auto', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
            background: s.border, color: '#fff', borderRadius: 999, padding: '2px 10px'
          }}>{risk}</span>
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="view-fade">
      <Topbar crumb="Field Watch" />
      <ToastContainer toasts={toasts} />

      <div className="page-head">
        <div>
          <div className="page-eyebrow">field</div>
          <h1 className="page-title">A <em>quiet daily check-in</em> for your land.</h1>
          <p className="page-lede">Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.</p>
        </div>
      </div>

      <LocationBar
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state}     setState={s => setProfile({ ...profile, state: s })}
        extra={
          <React.Fragment>
            <input
              className="input"
              value={city}
              onChange={e => setCity(e.target.value)}
              placeholder="Nearest city"
              style={{ width: 160 }}
              onKeyDown={e => e.key === 'Enter' && doScan()}
            />
            <button
              className="btn primary"
              onClick={() => doScan()}
              disabled={loading}
            >
              🛰 Scan now
            </button>
          </React.Fragment>
        }
      />

      {loading && <Loading label="Scanning field…" />}

      {error && !loading && (
        <ErrorCard
          title={
            error.status === 401 || error.status === 403
              ? 'Access denied'
              : error.status === 0
                ? 'Network error'
                : `Error ${error.status || ''}`
          }
          detail={error.detail || error.message}
          onRetry={() => doScan()}
        />
      )}

      {result && !loading && (
        <React.Fragment>

          {/* 1. Overall risk badge */}
          {(() => {
            const s = riskStyle(result.overall_risk);
            return (
              <div className="card rise" style={{
                background: s.bg, borderColor: s.border,
                textAlign: 'center', padding: '24px 20px', marginBottom: 18
              }}>
                <div style={{ fontSize: 36, marginBottom: 6 }}>{s.icon}</div>
                <div style={{
                  fontFamily: 'var(--display)', fontSize: 28,
                  color: s.color, letterSpacing: '0.04em'
                }}>
                  {result.overall_risk} RISK · {result.city}
                </div>
              </div>
            );
          })()}

          {/* 2. Weather metrics (4 tiles) */}
          {result.weather && (
            <div className="grid-4" style={{ marginBottom: 18 }}>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">Temperature</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.temp.toFixed(1)}°C</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>
                  feels like {result.weather.feels_like.toFixed(0)}°C
                </div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">Humidity</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.humidity}%</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>
                  {result.weather.description || '—'}
                </div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">Wind</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.wind.toFixed(0)} km/h</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>surface wind</div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">Rain 1h</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.rain_1h != null ? result.weather.rain_1h : 0} mm</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>last hour</div>
              </div>
            </div>
          )}

          {/* 3. Alert cards */}
          <div className="grid-2" style={{ marginBottom: 18 }}>
            {result.flood && (
              <AlertCard title="Flood risk" risk={result.flood.flood_risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  Rain 48h: <strong>{result.flood.rain_48h} mm</strong>
                </div>
              </AlertCard>
            )}

            {result.fire && (
              <AlertCard title="Fire" risk={result.fire.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  Hotspots nearby: <strong>{result.fire.hotspots_nearby}</strong>
                </div>
                {result.fire.source && (
                  <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>
                    source: {result.fire.source}
                  </div>
                )}
              </AlertCard>
            )}

            {result.locust && (
              <AlertCard title="Locust" risk={result.locust.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  Swarms nearby: <strong>{result.locust.swarms_nearby}</strong>
                </div>
                {result.locust.source && (
                  <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>
                    source: {result.locust.source}
                  </div>
                )}
              </AlertCard>
            )}

            {result.aqi && (
              <AlertCard
                title="Air Quality"
                risk={result.aqi.value > 200 ? 'HIGH' : result.aqi.value > 100 ? 'MEDIUM' : 'LOW'}
              >
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span className="bignum" style={{ fontSize: 36 }}>
                    <em>{result.aqi.value}</em>
                  </span>
                  <span style={{
                    fontSize: 12, fontWeight: 600,
                    background: riskStyle(result.aqi.value > 200 ? 'HIGH' : result.aqi.value > 100 ? 'MEDIUM' : 'LOW').border,
                    color: '#fff', borderRadius: 999, padding: '2px 10px'
                  }}>{result.aqi.label}</span>
                </div>
              </AlertCard>
            )}
          </div>

          {/* 4. Helplines table */}
          <div className="card rise" style={{ marginBottom: 18 }}>
            <div className="card-h">
              <h3>Emergency helplines</h3>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {GOVT_HELPLINES.map(([name, num, note], i) => (
                  <tr key={num} style={{
                    background: i % 2 === 0 ? 'transparent' : 'rgba(199,214,189,0.2)',
                  }}>
                    <td style={{ padding: '10px 12px', fontSize: 14, fontWeight: 500, color: 'var(--ink)' }}>
                      {name}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 14 }}>
                      <a href={`tel:${num}`} style={{ color: 'var(--leaf)', fontWeight: 600, textDecoration: 'none' }}>
                        {num}
                      </a>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--ink-faint)' }}>
                      {note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 5. WhatsApp builder */}
          <div className="card rise" style={{ marginBottom: 18 }}>
            <div className="card-h">
              <h3>Send to WhatsApp</h3>
            </div>
            <textarea
              readOnly
              className="input"
              rows={6}
              value={waMessage}
              style={{ width: '100%', fontFamily: 'monospace', fontSize: 12, marginBottom: 12, boxSizing: 'border-box' }}
            />
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                className="btn"
                onClick={() => {
                  navigator.clipboard.writeText(waMessage).then(() => addToast('Copied!', 'info'));
                }}
              >
                📋 Copy
              </button>
              <a
                href={`https://wa.me/?text=${encodeURIComponent(waMessage)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn primary"
              >
                📲 Open WhatsApp
              </a>
              {profile.phone && (
                <a
                  href={`https://wa.me/91${profile.phone.replace(/\D/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn ghost"
                >
                  Send to my number
                </a>
              )}
            </div>
          </div>

        </React.Fragment>
      )}
    </div>
  );
}

window.ViewField = ViewField;
