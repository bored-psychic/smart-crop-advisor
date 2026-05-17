// ViewAlerts — alert subscription management
const { useState, useEffect, useCallback } = React;

const ALERT_TYPE_LABELS = {
  frost:      { label: 'Frost Warning',   icon: '🌡️', desc: 'Temp drops below 4°C' },
  heavy_rain: { label: 'Heavy Rain',      icon: '🌧️', desc: 'Rain > 50mm in 48h' },
  pest_risk:  { label: 'Pest Risk',       icon: '🐛', desc: 'Seasonal pest peak for your crops' },
};

function HistoryCard({ items, t }) {
  if (!items.length) return (
    <div className="muted" style={{ padding: '20px 0', textAlign: 'center' }}>
      {t('No alerts sent yet.')}
    </div>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {items.map(item => {
        const color = item.severity === 'high' ? 'var(--berry)'
                    : item.severity === 'medium' ? 'var(--sun)' : 'var(--leaf)';
        return (
          <div key={item.id} style={{
            padding: '10px 14px', borderRadius: 12,
            background: 'var(--glass-bg)', border: `1px solid ${color}40`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                {item.alert_type.replace(/_/g, ' ')}
              </span>
              <span style={{ fontSize: 11, color: 'var(--ink-faint)' }}>
                {new Date(item.sent_at).toLocaleDateString()}
              </span>
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink-soft)', lineHeight: 1.5 }}>{item.message}</div>
          </div>
        );
      })}
    </div>
  );
}

function ViewAlerts({ profile, t }) {
  const [phone, setPhone]             = useState(profile.phone || '');
  const [district, setDistrict]       = useState(profile.village || '');
  const [state, setState]             = useState(profile.state || '');
  const [crops, setCrops]             = useState(profile.crop ? [profile.crop] : []);
  const [alertTypes, setAlertTypes]   = useState(['frost', 'heavy_rain', 'pest_risk']);
  const [subId, setSubId]             = useState(null);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState(null);
  const [success, setSuccess]         = useState('');
  const [history, setHistory]         = useState([]);
  const [histLoading, setHistLoading] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [pushLoading, setPushLoading] = useState(false);

  useEffect(() => {
    window.isPushEnabled && window.isPushEnabled().then(setPushEnabled);
  }, []);

  const fetchHistory = useCallback(async (ph) => {
    if (!ph) return;
    setHistLoading(true);
    try {
      const items = await window.api.alertsHistory(ph);
      setHistory(items);
    } catch (_) {
      setHistory([]);
    } finally {
      setHistLoading(false);
    }
  }, []);

  function toggleAlertType(type) {
    setAlertTypes(prev =>
      prev.includes(type) ? prev.filter(x => x !== type) : [...prev, type]
    );
  }

  async function handleSubscribe() {
    if (!phone)            { setError(t('Phone number required.')); return; }
    if (!state)            { setError(t('State required.')); return; }
    if (!crops.length)     { setError(t('Select at least one crop.')); return; }
    if (!alertTypes.length){ setError(t('Select at least one alert type.')); return; }
    setLoading(true); setError(null); setSuccess('');
    try {
      const res = await window.api.alertsSubscribe({
        phone, district, state, crops, alert_types: alertTypes,
      });
      setSubId(res.id);
      setSuccess(t('Subscribed! You will receive alerts at ') + phone);
      fetchHistory(phone);
    } catch (e) {
      setError(e.detail || e.message || t('Subscription failed.'));
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
      setSuccess(t('Unsubscribed successfully.'));
    } catch (e) {
      setError(e.detail || e.message || t('Unsubscribe failed.'));
    } finally {
      setLoading(false);
    }
  }

  async function handlePushToggle() {
    setPushLoading(true);
    try {
      if (!pushEnabled) {
        const ok = await window.initPush(phone);
        setPushEnabled(ok);
        if (ok) setSuccess(t('Browser push notifications enabled.'));
        else    setError(t('Push notifications not available or permission denied.'));
      }
    } catch (e) {
      setError(e.message || t('Push setup failed.'));
    } finally {
      setPushLoading(false);
    }
  }

  const cropOptions = window.ALL_CROPS || [];

  return (
    <div className="view-fade">
      <Topbar crumb={t('Alerts')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('alert system')}</div>
          <h1 className="page-title">{t('Know before')} <em>{t('the storm hits.')}</em></h1>
          <p className="page-lede">{t('Get frost, heavy rain, and pest risk alerts by SMS and browser push — before they reach your field.')}</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Subscribe')}</h3></div>

          <div className="page-eyebrow" style={{ marginBottom: 6 }}>{t('Phone')}</div>
          <input className="input" style={{ width: '100%', marginBottom: 14 }}
            type="tel" placeholder="+91 98765 43210"
            value={phone} onChange={e => setPhone(e.target.value)} />

          <div className="page-eyebrow" style={{ marginBottom: 6 }}>{t('District (optional)')}</div>
          <input className="input" style={{ width: '100%', marginBottom: 14 }}
            type="text" placeholder={t('e.g. Shimla')}
            value={district} onChange={e => setDistrict(e.target.value)} />

          <div className="page-eyebrow" style={{ marginBottom: 6 }}>{t('State')}</div>
          <select className="input" style={{ width: '100%', marginBottom: 18 }}
            value={state} onChange={e => setState(e.target.value)}>
            <option value="">{t('Select state…')}</option>
            {(window.INDIA_STATES || []).map(s => <option key={s}>{s}</option>)}
          </select>

          <div className="page-eyebrow" style={{ marginBottom: 8 }}>{t('Crops')}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18 }}>
            {cropOptions.slice(0, 16).map(crop => {
              const sel = crops.includes(crop);
              return (
                <button key={crop}
                  onClick={() => setCrops(prev => sel ? prev.filter(c => c !== crop) : [...prev, crop])}
                  style={{
                    padding: '4px 12px', borderRadius: 999, fontSize: 12, cursor: 'pointer', border: '1px solid',
                    background: sel ? 'var(--leaf)' : 'transparent',
                    color: sel ? '#fff' : 'var(--ink-soft)',
                    borderColor: sel ? 'var(--leaf)' : 'var(--glass-border)',
                  }}>
                  {crop}
                </button>
              );
            })}
          </div>

          <div className="page-eyebrow" style={{ marginBottom: 8 }}>{t('Alert types')}</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
            {Object.entries(ALERT_TYPE_LABELS).map(([key, meta]) => {
              const on = alertTypes.includes(key);
              return (
                <div key={key} onClick={() => toggleAlertType(key)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px',
                    borderRadius: 12, cursor: 'pointer',
                    background: on ? 'rgba(127,217,140,0.10)' : 'var(--glass-bg)',
                    border: `1px solid ${on ? 'rgba(127,217,140,0.4)' : 'var(--glass-border)'}`,
                  }}>
                  <span style={{ fontSize: 22 }}>{meta.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{t(meta.label)}</div>
                    <div style={{ fontSize: 11, color: 'var(--ink-faint)' }}>{t(meta.desc)}</div>
                  </div>
                  <div style={{
                    width: 18, height: 18, borderRadius: 4,
                    border: `2px solid ${on ? 'var(--leaf)' : 'var(--glass-border)'}`,
                    background: on ? 'var(--leaf)' : 'transparent', flexShrink: 0,
                  }} />
                </div>
              );
            })}
          </div>

          {error   && <div style={{ color: 'var(--berry)', fontSize: 13, marginBottom: 10 }}>{error}</div>}
          {success && <div style={{ color: 'var(--leaf)',  fontSize: 13, marginBottom: 10 }}>{success}</div>}

          <div style={{ display: 'flex', gap: 10 }}>
            {!subId ? (
              <button className="btn primary" onClick={handleSubscribe} disabled={loading}>
                {loading ? t('Subscribing…') : t('Subscribe to Alerts')}
              </button>
            ) : (
              <button className="btn" onClick={handleUnsubscribe} disabled={loading}
                style={{ color: 'var(--berry)', borderColor: 'var(--berry)' }}>
                {loading ? t('…') : t('Unsubscribe')}
              </button>
            )}
            <button className="btn ghost" onClick={handlePushToggle} disabled={pushLoading || pushEnabled}>
              {pushEnabled ? t('🔔 Push On') : pushLoading ? t('Setting up…') : t('Enable Push')}
            </button>
          </div>
        </div>

        <div className="card rise rise-2">
          <div className="card-h">
            <h3>{t('Alert History')}</h3>
            {phone && (
              <button className="btn ghost" style={{ fontSize: 12 }}
                onClick={() => fetchHistory(phone)}>
                {histLoading ? t('…') : t('Refresh')}
              </button>
            )}
          </div>
          {histLoading && <Loading label={t('Loading history…')} />}
          {!histLoading && <HistoryCard items={history} t={t} />}
        </div>
      </div>
    </div>
  );
}

window.ViewAlerts = ViewAlerts;
