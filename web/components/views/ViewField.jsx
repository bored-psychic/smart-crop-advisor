// ViewField — live field-watch scan: weather, flood, fire, locust, AQI + helplines + WhatsApp builder + alert subscription
const { useState, useEffect, useCallback, useMemo } = React;

const ALERT_TYPES = [
  { k: 'frost',      icon: '🌡️', label: 'Frost Warning',  desc: 'Temp drops below 4°C' },
  { k: 'heavy_rain', icon: '🌧️', label: 'Heavy Rain',     desc: 'Rain > 50mm in 48h' },
  { k: 'pest_risk',  icon: '🐛', label: 'Pest Risk',      desc: 'Seasonal peak for your crops' },
];

function AlertSubscribeSection({ profile, t }) {
  const [phone, setPhone]           = useState(profile.phone || '');
  const [alertTypes, setAlertTypes] = useState(['frost', 'heavy_rain', 'pest_risk']);
  const [subId, setSubId]           = useState(null);
  const [loading, setLoading]       = useState(false);
  const [pushLoading, setPushLoading] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [msg, setMsg]               = useState(null); // { text, ok }

  useEffect(() => {
    window.isPushEnabled && window.isPushEnabled().then(setPushEnabled);
  }, []);

  // keep phone in sync if profile updates after login
  useEffect(() => { if (profile.phone) setPhone(profile.phone); }, [profile.phone]);

  function toggleType(k) {
    setAlertTypes(prev => prev.includes(k) ? prev.filter(x => x !== k) : [...prev, k]);
  }

  async function handleSubscribe() {
    if (!phone) { setMsg({ text: t('Phone number required.'), ok: false }); return; }
    if (!profile.state) { setMsg({ text: t('Set your state in the location bar above first.'), ok: false }); return; }
    if (!alertTypes.length) { setMsg({ text: t('Pick at least one alert type.'), ok: false }); return; }
    setLoading(true); setMsg(null);
    try {
      const res = await window.api.alertsSubscribe({
        phone,
        district: profile.village || null,
        state: profile.state,
        crops: profile.crop ? [profile.crop] : [],
        alert_types: alertTypes,
      });
      setSubId(res.id);
      setMsg({ text: t('Subscribed! Alerts will be sent to ') + phone, ok: true });
    } catch (e) {
      setMsg({ text: e.detail || e.message || t('Subscription failed.'), ok: false });
    } finally {
      setLoading(false);
    }
  }

  async function handleUnsubscribe() {
    if (!subId) return;
    setLoading(true);
    try {
      await window.api.alertsUnsubscribe(subId);
      setSubId(null);
      setMsg({ text: t('Unsubscribed.'), ok: true });
    } catch (e) {
      setMsg({ text: e.detail || e.message || t('Failed.'), ok: false });
    } finally {
      setLoading(false);
    }
  }

  async function handlePush() {
    setPushLoading(true); setMsg(null);
    try {
      const ok = await window.initPush(phone);
      setPushEnabled(ok);
      setMsg(ok
        ? { text: t('Browser push notifications enabled.'), ok: true }
        : { text: t('Permission denied or push not supported.'), ok: false });
    } catch (e) {
      setMsg({ text: e.message || t('Push setup failed.'), ok: false });
    } finally {
      setPushLoading(false);
    }
  }

  return (
    <div className="card rise" style={{ marginBottom: 18 }}>
      <div className="card-h">
        <h3>{t('Alert Subscriptions')}</h3>
        {subId && <span className="tag" style={{ color: 'var(--leaf)', borderColor: 'rgba(127,217,140,0.4)', background: 'rgba(127,217,140,0.10)' }}>{t('Active')}</span>}
      </div>
      <p className="muted small" style={{ marginBottom: 14 }}>
        {t('Get frost, heavy rain, and pest risk alerts by SMS — based on your field location and crop.')}
      </p>

      {/* Phone */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <input
          className="input"
          type="tel"
          placeholder="+91 98765 43210"
          value={phone}
          onChange={e => setPhone(e.target.value)}
          style={{ flex: 1, minWidth: 180 }}
        />
        {!subId ? (
          <button className="btn primary" onClick={handleSubscribe} disabled={loading}>
            {loading ? t('…') : t('Subscribe')}
          </button>
        ) : (
          <button className="btn" onClick={handleUnsubscribe} disabled={loading}
            style={{ color: 'var(--berry)', borderColor: 'var(--berry)' }}>
            {loading ? t('…') : t('Unsubscribe')}
          </button>
        )}
        <button className="btn ghost" onClick={handlePush} disabled={pushLoading || pushEnabled}>
          {pushEnabled ? t('🔔 Push On') : pushLoading ? t('…') : t('Enable Push')}
        </button>
      </div>

      {/* Alert type toggles */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {ALERT_TYPES.map(({ k, icon, label, desc }) => {
          const on = alertTypes.includes(k);
          return (
            <button key={k} onClick={() => toggleType(k)} title={t(desc)} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px',
              borderRadius: 999, fontSize: 12, cursor: 'pointer', border: '1px solid',
              background: on ? 'rgba(127,217,140,0.14)' : 'transparent',
              color: on ? 'var(--leaf)' : 'var(--ink-soft)',
              borderColor: on ? 'rgba(127,217,140,0.5)' : 'var(--glass-border)',
              fontFamily: 'var(--body)',
            }}>
              <span>{icon}</span> {t(label)}
            </button>
          );
        })}
      </div>

      {msg && (
        <div style={{ fontSize: 13, color: msg.ok ? 'var(--leaf)' : 'var(--berry)', marginTop: 4 }}>
          {msg.text}
        </div>
      )}
    </div>
  );
}

/* ---- Risk badge helpers (module scope so AlertCard can use them) ---- */
function riskStyle(risk) {
  if (risk === 'HIGH')   return { bg: 'rgba(232,112,95,0.14)', border: 'var(--berry)', color: 'var(--berry)', icon: '🔴' };
  if (risk === 'MEDIUM') return { bg: 'rgba(240,192,96,0.14)', border: 'var(--sun)',   color: 'var(--sun)',   icon: '🟡' };
  return                        { bg: 'var(--leaf-soft)',      border: 'var(--leaf)',  color: 'var(--leaf)',  icon: '🟢' };
}

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

function ViewField({ profile, setProfile, t, fieldData, fieldLoading }) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(fieldData || null);

  // Reflect prefetched data from App as it arrives
  useEffect(() => { if (fieldData) setResult(fieldData); }, [fieldData]);
  const { toasts, add: addToast } = useToast();

  const doScan = useCallback(async (scanCity) => {
    const target = (scanCity || profile.village || '').trim();
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
  }, [profile.village]);

  // App-level prefetch covers village changes; doScan() remains for manual "Scan now"
  useEffect(() => { setLoading(!!fieldLoading); }, [fieldLoading]);

  /* ---- WhatsApp message ---- */
  const waMessage = useMemo(() => {
    if (!result) return '';
    return [
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
    ].filter(Boolean).join('\n');
  }, [result, profile]);

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
        village={profile.village} setVillage={v => setProfile({ ...profile, village: v })}
        state={profile.state}     setState={s => setProfile({ ...profile, state: s })}
        extra={
          <button
            className="btn primary"
            onClick={() => doScan()}
            disabled={loading}
          >
            {t('🛰 Scan now')}
          </button>
        }
      />

      {loading && <Loading label={t('Scanning field…')} />}

      {error && !loading && (
        <ErrorCard
          title={
            error.status === 401 || error.status === 403
              ? t('Access denied')
              : error.status === 0
                ? t('Network error')
                : t('Error') + ' ' + (error.status || '')
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
                  {result.overall_risk} {t('RISK')} · {result.city}
                </div>
              </div>
            );
          })()}

          {/* 2. Weather metrics (4 tiles) */}
          {result.weather && (
            <div className="grid-4" style={{ marginBottom: 18 }}>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">{t('Temperature')}</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.temp?.toFixed(1) ?? '—'}°C</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>
                  {t('feels like')} {result.weather.feels_like?.toFixed(0) ?? '—'}°C
                </div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">{t('Humidity')}</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.humidity}%</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>
                  {result.weather.description || '—'}
                </div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">{t('Wind')}</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.wind?.toFixed(0) ?? '—'} km/h</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>{t('surface wind')}</div>
              </div>
              <div className="card rise" style={{ padding: '18px 20px' }}>
                <div className="page-eyebrow">{t('Rain 1h')}</div>
                <div className="bignum" style={{ fontSize: 32, marginTop: 6 }}>
                  <em>{result.weather.rain_1h != null ? result.weather.rain_1h : 0} mm</em>
                </div>
                <div className="muted small" style={{ marginTop: 4 }}>{t('last hour')}</div>
              </div>
            </div>
          )}

          {/* 3. Alert cards */}
          <div className="grid-2" style={{ marginBottom: 18 }}>
            {result.flood && (
              <AlertCard title={t('Flood risk')} risk={result.flood.flood_risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  {t('Rain 48h:')} <strong>{result.flood.rain_48h} mm</strong>
                </div>
              </AlertCard>
            )}

            {result.fire && (
              <AlertCard title={t('Fire')} risk={result.fire.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  {t('Hotspots nearby:')} <strong>{result.fire.hotspots_nearby}</strong>
                </div>
                {result.fire.source && (
                  <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>
                    {t('source:')} {result.fire.source}
                  </div>
                )}
              </AlertCard>
            )}

            {result.locust && (
              <AlertCard title={t('Locust')} risk={result.locust.risk}>
                <div style={{ color: 'var(--ink-soft)', fontSize: 14 }}>
                  {t('Swarms nearby:')} <strong>{result.locust.swarms_nearby}</strong>
                </div>
                {result.locust.source && (
                  <div style={{ fontSize: 11, color: 'var(--ink-faint)', marginTop: 4 }}>
                    {t('source:')} {result.locust.source}
                  </div>
                )}
              </AlertCard>
            )}

            {result.aqi && (
              <AlertCard
                title={t('Air Quality')}
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
              <h3>{t('Emergency helplines')}</h3>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                {GOVT_HELPLINES.map(([name, num, note], i) => (
                  <tr key={num} style={{
                    background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.06)',
                  }}>
                    <td style={{ padding: '10px 12px', fontSize: 14, fontWeight: 500, color: 'var(--ink)' }}>
                      {t(name)}
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 14 }}>
                      <a href={`tel:${num}`} style={{ color: 'var(--leaf)', fontWeight: 600, textDecoration: 'none' }}>
                        {num}
                      </a>
                    </td>
                    <td style={{ padding: '10px 12px', fontSize: 12, color: 'var(--ink-faint)' }}>
                      {t(note)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 5. WhatsApp builder */}
          <div className="card rise" style={{ marginBottom: 18 }}>
            <div className="card-h">
              <h3>{t('Send to WhatsApp')}</h3>
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
                  const handleCopy = () => {
                    if (navigator.clipboard) {
                      navigator.clipboard.writeText(waMessage).then(() => addToast('Copied!', 'info')).catch(() => {
                        // fallback to execCommand
                        const ta = document.createElement('textarea');
                        ta.value = waMessage;
                        document.body.appendChild(ta);
                        ta.select();
                        document.execCommand('copy');
                        document.body.removeChild(ta);
                        addToast('Copied!', 'info');
                      });
                    } else {
                      const ta = document.createElement('textarea');
                      ta.value = waMessage;
                      document.body.appendChild(ta);
                      ta.select();
                      document.execCommand('copy');
                      document.body.removeChild(ta);
                      addToast('Copied!', 'info');
                    }
                  };
                  handleCopy();
                }}
              >
                {t('📋 Copy')}
              </button>
              <a
                href={`https://wa.me/?text=${encodeURIComponent(waMessage)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn primary"
              >
                {t('📲 Open WhatsApp')}
              </a>
              {profile.phone && (
                <a
                  href={`https://wa.me/91${profile.phone.replace(/\D/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn ghost"
                >
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
