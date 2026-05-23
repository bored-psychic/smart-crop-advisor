// ViewField — live field-watch scan: weather, flood, fire, locust, AQI + helplines + WhatsApp builder + alert subscription
// API calls + WhatsApp: hooks/useFieldData.js
// AlertSubscribeSection: hooks/useAlertSubscribe.js

/* ---- Risk badge helpers ---- */
function riskStyle(risk) {
  if (risk === 'HIGH')   return { bg: 'rgba(232,112,95,0.14)', border: 'var(--berry)', color: 'var(--berry)', icon: '🔴' };
  if (risk === 'MEDIUM') return { bg: 'rgba(240,192,96,0.14)', border: 'var(--sun)',   color: 'var(--sun)',   icon: '🟡' };
  return                        { bg: 'var(--leaf-soft)',      border: 'var(--leaf)',  color: 'var(--leaf)',  icon: '🟢' };
}

function AlertCard({ title, risk, children }) {
  const s = riskStyle(risk);
  return (
    <div className="card rise" style={{ borderColor: s.border, background: s.bg }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 18 }}>{s.icon}</span>
        <span style={{ fontFamily: 'var(--display)', fontSize: 16, color: s.color }}>{title}</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', background: s.border, color: '#fff', borderRadius: 999, padding: '2px 10px' }}>{risk}</span>
      </div>
      {children}
    </div>
  );
}

function ViewField({ profile, setProfile, t, fieldData, fieldLoading }) {
  const { loading, error, result, doScan, waMessage } = window.useFieldData(profile, fieldData, fieldLoading);
  const { toasts, add: addToast } = useToast();

  function handleCopy() {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(waMessage).then(() => addToast('Copied!', 'info')).catch(copyFallback);
    } else {
      copyFallback();
    }
    function copyFallback() {
      const ta = document.createElement('textarea');
      ta.value = waMessage;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      addToast('Copied!', 'info');
    }
  }

  return (
    <div className="view-fade">
      <Topbar crumb={t('Field Watch')} />
      <ToastContainer toasts={toasts} />

      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('field')}</div>
          <h1 className="page-title">{t('A')} <em>{t('quiet daily check-in')}</em> {t('for your land.')}</h1>
          <p className="page-lede">{t("Weather, fires, locusts, soil — all gathered in one calm view. Just the things you need to know today.")}</p>
        </div>
      </div>

      <LocationBar
        t={t}
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state}     setState={s => setProfile({ ...profile, state: s })}
        extra={<button className="btn primary" onClick={() => doScan()} disabled={loading}>{t('🛰 Scan now')}</button>}
      />

      {loading && <Loading label={t('Scanning field…')} />}

      {error && !loading && (
        <ErrorCard t={t}
          title={error.status === 401 || error.status === 403 ? t('Access denied') : error.status === 0 ? t('Network error') : t('Error') + ' ' + (error.status || '')}
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
              <div className="card rise" style={{ background: s.bg, borderColor: s.border, textAlign: 'center', padding: '24px 20px', marginBottom: 18 }}>
                <div style={{ fontSize: 36, marginBottom: 6 }}>{s.icon}</div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 28, color: s.color, letterSpacing: '0.04em' }}>
                  {result.overall_risk} {t('RISK')} · {result.city}
                </div>
              </div>
            );
          })()}

          {/* 2. Weather metrics */}
          {result.weather && (
            <div className="grid-4" style={{ marginBottom: 18 }}>
              {[
                { label: t('Temperature'), big: `${result.weather.temp?.toFixed(1) ?? '—'}°C`, sub: `${t('feels like')} ${result.weather.feels_like?.toFixed(0) ?? '—'}°C` },
                { label: t('Humidity'),    big: `${result.weather.humidity}%`,                  sub: result.weather.description || '—' },
                { label: t('Wind'),        big: `${result.weather.wind?.toFixed(0) ?? '—'} km/h`, sub: t('surface wind') },
                { label: t('Rain 1h'),     big: `${result.weather.rain_1h != null ? result.weather.rain_1h : 0} mm`, sub: t('last hour') },
              ].map(({ label, big, sub }) => (
                <div key={label} className="card rise" style={{ padding: '18px 20px' }}>
                  <div className="page-eyebrow">{label}</div>
                  <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}><em>{big}</em></div>
                  <div className="muted small" style={{ marginTop: 4 }}>{sub}</div>
                </div>
              ))}
            </div>
          )}

          {/* 3. Alert cards */}
          <div className="grid-2" style={{ marginBottom: 18 }}>
            {result.flood && (
              <AlertCard title={t('Flood risk')} risk={result.flood.flood_risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>{t('Rain 48h:')} <strong>{result.flood.rain_48h} mm</strong></div>
              </AlertCard>
            )}
            {result.fire && (
              <AlertCard title={t('Fire')} risk={result.fire.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>{t('Hotspots nearby:')} <strong>{result.fire.hotspots_nearby}</strong></div>
                {result.fire.source && <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>{t('source:')} {result.fire.source}</div>}
              </AlertCard>
            )}
            {result.locust && (
              <AlertCard title={t('Locust')} risk={result.locust.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>{t('Swarms nearby:')} <strong>{result.locust.swarms_nearby}</strong></div>
                {result.locust.source && <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>{t('source:')} {result.locust.source}</div>}
              </AlertCard>
            )}
            {result.aqi && (
              <AlertCard title={t('Air Quality')} risk={result.aqi.value > 200 ? 'HIGH' : result.aqi.value > 100 ? 'MEDIUM' : 'LOW'}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                  <span className="bignum" style={{ fontSize: 36 }}><em>{result.aqi.value}</em></span>
                  <span style={{ fontSize: 12, fontWeight: 600, background: riskStyle(result.aqi.value > 200 ? 'HIGH' : result.aqi.value > 100 ? 'MEDIUM' : 'LOW').border, color: '#fff', borderRadius: 999, padding: '2px 10px' }}>{result.aqi.label}</span>
                </div>
              </AlertCard>
            )}
          </div>

          {/* 4. Helplines table */}
          <div className="card rise" style={{ marginBottom: 18 }}>
            <div className="card-h"><h3>{t('Emergency helplines')}</h3></div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {GOVT_HELPLINES.map(([name, num, note], i) => (
                  <tr key={num} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.06)' }}>
                    <td style={{ padding: '10px 12px', fontSize: 14, fontWeight: 500, color: 'var(--ink)' }}>{t(name)}</td>
                    <td style={{ padding: '10px 12px', fontSize: 14 }}>
                      <a href={`tel:${num}`} style={{ color: 'var(--leaf)', fontWeight: 600, textDecoration: 'none' }}>{num}</a>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--ink-faint)' }}>{t(note)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 5. WhatsApp builder */}
          <div className="card rise" style={{ marginBottom: 18 }}>
            <div className="card-h"><h3>{t('Send to WhatsApp')}</h3></div>
            <textarea readOnly className="input" rows={6} value={waMessage}
              style={{ width: '100%', fontFamily: 'monospace', fontSize: 12, marginBottom: 12, boxSizing: 'border-box' }} />
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
              <button className="btn" onClick={handleCopy}>{t('📋 Copy')}</button>
              <a href={`https://wa.me/?text=${encodeURIComponent(waMessage)}`} target="_blank" rel="noopener noreferrer" className="btn primary">
                {t('📲 Open WhatsApp')}
              </a>
              {profile.phone && (
                <a href={`https://wa.me/91${profile.phone.replace(/\D/g, '')}`} target="_blank" rel="noopener noreferrer" className="btn ghost">
                  {t('Send to my number')}
                </a>
              )}
            </div>
          </div>
        </React.Fragment>
      )}

      <AlertSubscribeSection profile={profile} t={t} />
    </div>
  );
}

window.ViewField = ViewField;
