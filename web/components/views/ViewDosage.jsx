// ViewDosage — wired to /api/dosage/recommend
const { useState } = React;

const KNOWN_PEST_IDS = [
  'armyworm', 'aphids', 'stem_borer', 'whitefly',
  'fusarium_wilt', 'blast', 'blight', 'leaf_curl',
  'powdery_mildew', 'red_mite',
];

function ViewDosage({ profile, t }) {
  const [pestId, setPestId]           = useState('');
  const [crop, setCrop]               = useState(profile.crop || '');
  const [cropStageDays, setCropStage] = useState(30);
  const [areaAcres, setAreaAcres]     = useState(1.0);
  const [state, setState]             = useState(profile.state || '');

  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [result, setResult]   = useState(null);
  const { add: toast }        = useToast();

  async function handleSubmit() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await window.api.dosageRecommend({
        pest_id: pestId,
        crop,
        crop_stage_days: cropStageDays,
        area_acres: areaAcres,
        state,
      });
      setResult(data);
    } catch (err) {
      setError(err);
      toast('Dosage calculation failed', 'error');
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 10,
    border: '1px solid var(--glass-border)',
    background: 'var(--glass-bg)',
    color: 'var(--ink)',
    fontSize: 14,
    boxSizing: 'border-box',
  };

  const labelStyle = {
    fontSize: 13,
    color: 'var(--ink-soft)',
    display: 'block',
    marginBottom: 4,
  };

  return (
    <div className="view-fade">
      <Topbar crumb={t('Dosage Advisor')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('dosage advisor')}</div>
          <h1 className="page-title">{t('Right dose,')} <em>{t('right time.')}</em></h1>
          <p className="page-lede">{t("Tell us the pest and your crop. We'll calculate the exact quantity and cost.")}</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Pest & Crop')}</h3></div>
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>{t('Pest')}</label>
            <input
              type="text"
              list="pest-list"
              value={pestId}
              onChange={e => setPestId(e.target.value)}
              placeholder={t('e.g. armyworm')}
              style={inputStyle}
            />
            <datalist id="pest-list">
              {KNOWN_PEST_IDS.map(p => <option key={p} value={p} />)}
            </datalist>
          </div>
          <div>
            <label style={labelStyle}>{t('Crop')}</label>
            <input
              type="text"
              value={crop}
              onChange={e => setCrop(e.target.value)}
              placeholder={t('e.g. maize')}
              style={inputStyle}
            />
          </div>
        </div>
        <div className="card rise rise-2">
          <div className="card-h"><h3>{t('Field Details')}</h3></div>
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>{t('Crop Age (days)')}</label>
            <input
              type="number"
              value={cropStageDays}
              min={0}
              max={365}
              onChange={e => setCropStage(parseInt(e.target.value) || 0)}
              style={inputStyle}
            />
          </div>
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>{t('Area (acres)')}</label>
            <input
              type="number"
              value={areaAcres}
              min={0.1}
              max={100}
              step={0.1}
              onChange={e => setAreaAcres(parseFloat(e.target.value) || 1)}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>{t('State')}</label>
            <input
              type="text"
              value={state}
              onChange={e => setState(e.target.value)}
              placeholder={t('e.g. Maharashtra')}
              style={inputStyle}
            />
          </div>
        </div>
      </div>

      <button className="btn btn-full" onClick={handleSubmit} disabled={loading} style={{ marginTop: 18 }}>
        {loading ? t('Calculating…') : t('Get Dosage')}
      </button>

      {loading && <Loading label={t('Calculating dosage…')} />}

      {error && !loading && (
        <ErrorCard title={t('Could not calculate dosage')} detail={error.detail} onRetry={handleSubmit} />
      )}

      {result && !loading && (
        <>
          <div className="card rise" style={{ marginTop: 18 }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ fontFamily: 'var(--display)', fontSize: 28, fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.01em' }}>
                  {result.chemical_name} <span style={{ color: 'var(--leaf)', fontWeight: 400 }}>{result.formulation}</span>
                </div>
                <p style={{ fontStyle: 'italic', color: 'var(--ink-soft)', marginTop: 8, marginBottom: 0 }}>{result.narrative}</p>
              </div>
              {result.source === 'llm_fallback' && (
                <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--sun)', background: 'rgba(240,192,96,0.14)', padding: '3px 10px', borderRadius: 99, whiteSpace: 'nowrap' }}>
                  AI estimate — verify with agronomist
                </span>
              )}
            </div>
          </div>

          <div className="card rise" style={{ marginTop: 14 }}>
            <div className="card-h"><h3>{t('Application')}</h3></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginTop: 10 }}>
              <div>
                <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 2 }}>📦 {t('Quantity')}</div>
                <div style={{ fontWeight: 600 }}>{result.total_quantity_ml} ml</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 2 }}>💧 {t('Water')}</div>
                <div style={{ fontWeight: 600 }}>{result.water_litres} L</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 2 }}>⏰ {t('Timing')}</div>
                <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{result.timing}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: 'var(--ink-faint)', marginBottom: 2 }}>🔄 {t('Reapply after')}</div>
                <div style={{ fontWeight: 600 }}>{result.reapply_after_days} {t('days')}</div>
              </div>
            </div>
          </div>

          <div className="card rise" style={{ marginTop: 14 }}>
            <div className="card-h"><h3>{t('Cost & ROI')}</h3></div>
            <div style={{ marginTop: 10 }}>
              <div style={{ marginBottom: 10 }}>
                <span style={{ fontSize: 13, color: 'var(--ink-soft)' }}>{t('Total cost')}: </span>
                <span style={{ fontWeight: 600, fontSize: 18 }}>₹{result.total_cost_inr}</span>
              </div>
              {result.roi_protected_inr != null ? (
                <>
                  <div style={{ marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: 'var(--ink-soft)' }}>{t('Yield protected')}: </span>
                    <span style={{ fontWeight: 600 }}>₹{result.roi_protected_inr}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 13, color: 'var(--ink-soft)' }}>{t('ROI')}: </span>
                    <span style={{ fontWeight: 600, color: 'var(--leaf)', fontSize: 18 }}>
                      {(result.roi_protected_inr / result.total_cost_inr).toFixed(1)}× {t('return')}
                    </span>
                  </div>
                </>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--ink-faint)' }}>
                  {t('Market price unavailable for ROI calculation')}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

window.ViewDosage = ViewDosage;
