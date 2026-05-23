// AlertSubscribeSection — SMS + push alert subscription UI for ViewField
// Extracted to keep ViewField.jsx under 250 lines.

(function () {
  const { useState, useEffect } = React;

  const ALERT_TYPES = [
    { k: 'frost',      icon: '🌡️', label: 'Frost Warning', desc: 'Temp drops below 4°C' },
    { k: 'heavy_rain', icon: '🌧️', label: 'Heavy Rain',    desc: 'Rain > 50mm in 48h' },
    { k: 'pest_risk',  icon: '🐛', label: 'Pest Risk',     desc: 'Seasonal peak for your crops' },
  ];

  function AlertSubscribeSection({ profile, t }) {
    const [phone, setPhone]             = useState(profile.phone || '');
    const [alertTypes, setAlertTypes]   = useState(['frost', 'heavy_rain', 'pest_risk']);
    const [subId, setSubId]             = useState(null);
    const [loading, setLoading]         = useState(false);
    const [pushLoading, setPushLoading] = useState(false);
    const [pushEnabled, setPushEnabled] = useState(false);
    const [msg, setMsg]                 = useState(null);

    useEffect(() => {
      window.isPushEnabled && window.isPushEnabled().then(setPushEnabled);
    }, []);

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
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
          <input className="input" type="tel" placeholder="+91 98765 43210" value={phone}
            onChange={e => setPhone(e.target.value)} style={{ flex: 1, minWidth: 180 }} />
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

  window.AlertSubscribeSection = AlertSubscribeSection;
})();
