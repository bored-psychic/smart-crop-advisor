// ViewDisease — photo flow with real API
// Photo panel form state and API calls live in hooks/usePhotoPanelForm.js

function SevTag({ severity }) {
  const color = severity === 'High'   ? 'var(--berry)'
              : severity === 'Medium' ? '#A06B1F'
              : 'var(--leaf)';
  return (
    <span className="tag" style={{ color, borderColor: color + '40', background: color + '14' }}>
      {severity}
    </span>
  );
}

function Top3Bars({ top3, t }) {
  if (!top3 || top3.length === 0) return null;
  const max = top3[0]?.[1] || 1;
  return (
    <div style={{ marginTop: 14 }}>
      <div className="page-eyebrow" style={{ marginBottom: 8 }}>{t('top matches')}</div>
      {top3.map(([name, pct]) => (
        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{ width: 120, fontSize: 12, color: 'var(--ink-soft)', textAlign: 'right' }}>{name}</div>
          <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.10)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${(pct / max) * 100}%`, height: '100%', background: 'var(--leaf)', borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ width: 40, fontSize: 12, color: 'var(--ink-faint)', textAlign: 'right' }}>{pct}%</div>
        </div>
      ))}
    </div>
  );
}

function PhotoResult({ result, t, price, priceLoading, areaAcres }) {
  return (
    <div className="rise">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
        <span className="tag" style={{ color: 'var(--ink-faint)', borderColor: 'var(--line-2)', fontSize: 11 }}>
          {t('via')} {result.model_used || 'Vision API'}
        </span>
        <SevTag severity={result.severity} />
      </div>
      <div style={{ fontFamily: 'var(--display)', fontSize: 30, color: 'var(--ink)', letterSpacing: '-0.01em', marginTop: 4 }}>
        {result.disease}
      </div>
      {result.action && (
        <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(240,192,96,0.16)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--sun)' }}>{t('right now')}</div>
          <div style={{ marginTop: 4 }}>{result.action}</div>
        </div>
      )}
      {result.treatment && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('treatment')}</div>
          <div style={{ marginTop: 4 }}>{result.treatment}</div>
          {(priceLoading || price) && (
            <div style={{ marginTop: 10, padding: '10px 12px', background: 'rgba(127,217,140,0.10)', border: '1px solid rgba(127,217,140,0.28)', borderRadius: 10 }}>
              <div className="page-eyebrow" style={{ color: 'var(--leaf)', marginBottom: 4 }}>
                {t('estimated cost')} · {areaAcres} {t('acres')}
              </div>
              {priceLoading && <div className="muted small" style={{ fontStyle: 'italic' }}>{t('Estimating cost…')}</div>}
              {price && !priceLoading && (
                <>
                  <div style={{ fontFamily: 'var(--display)', fontSize: 22, color: 'var(--ink)' }}>{price.cost_range}</div>
                  <div className="muted small" style={{ marginTop: 3 }}>₹{price.per_acre_inr.toLocaleString()}/acre · {price.notes}</div>
                </>
              )}
            </div>
          )}
        </div>
      )}
      {result.prevention && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'var(--glass-bg-subtle)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>{t('prevention')}</div>
          <div style={{ marginTop: 4 }}>{result.prevention}</div>
        </div>
      )}
      <Top3Bars top3={result.top3} t={t} />
    </div>
  );
}

function PhotoPanel({ t, areaAcres }) {
  const {
    cropList, cropsLoading, cropType, setCropType,
    drag, setDrag,
    loading, result, error,
    price, priceLoading,
    file, fileRef,
    analyzeFile, handleFileChange, onDrop,
  } = window.usePhotoPanelForm(areaAcres);

  function errorMsg(e) {
    if (!e) return t('Something went wrong.');
    if (e.status === 401 || e.status === 403) return t('API key issue — check your config.js setup.');
    if (!e.status && e.message) return t('No connection — check your network and try again.');
    return e.detail || e.message || t('Analysis failed.');
  }

  return (
    <div className="grid-2">
      <div className="card rise rise-1">
        <div className="card-h">
          <h3>{t('Send a photo')}</h3>
          {cropsLoading ? (
            <span className="muted small" style={{ fontStyle: 'italic' }}>{t('loading crops…')}</span>
          ) : (
            <select className="input" style={{ width: 140 }} value={cropType} onChange={e => setCropType(e.target.value)}>
              {(cropList || window._FALLBACK_CROPS).map(c => <option key={c}>{c}</option>)}
            </select>
          )}
        </div>
        <div
          className="drop"
          onClick={() => fileRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          style={{
            borderColor: drag ? 'var(--leaf)' : 'var(--glass-border-strong)',
            background: drag ? 'rgba(127,217,140,0.14)' : 'var(--glass-bg-subtle)',
          }}
        >
          <div style={{ fontSize: 36 }}>🍃</div>
          <div style={{ marginTop: 10, fontSize: 14 }}><strong>{t('Drop a leaf photo here')}</strong></div>
          <div className="muted small" style={{ marginTop: 4 }}>{t('or click to choose · jpg, png, webp')}</div>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFileChange} />
        </div>
      </div>

      <div className="card rise rise-2">
        <div className="card-h">
          <h3>{t('What we see')}</h3>
          {result && <SevTag severity={result.severity} />}
        </div>
        {!loading && !result && !error && (
          <div className="muted" style={{ padding: '30px 0', textAlign: 'center' }}>{t("Send a photo and we'll have a look. 🌿")}</div>
        )}
        {loading && <Loading label={t('Analyzing leaf…')} />}
        {!loading && error && (
          <ErrorCard
            t={t}
            title={t('Could not analyze photo')}
            detail={errorMsg(error)}
            onRetry={() => { if (file) analyzeFile(file); }}
          />
        )}
        {!loading && result && (
          <PhotoResult result={result} t={t} price={price} priceLoading={priceLoading} areaAcres={areaAcres} />
        )}
      </div>
    </div>
  );
}

function ViewDisease({ profile, t, areaAcres = 1.0 }) {
  return (
    <div className="view-fade">
      <Topbar crumb={t('Leaf Doctor')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('leaf doctor')}</div>
          <h1 className="page-title">{t('A')} <em>{t('second pair of eyes')}</em> {t('for sick leaves.')}</h1>
          <p className="page-lede">{t("Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.")}</p>
        </div>
      </div>
      <PhotoPanel t={t} areaAcres={areaAcres} />
    </div>
  );
}

window.ViewDisease = ViewDisease;
