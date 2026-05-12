// ViewDisease — photo flow with real API
const { useState, useEffect, useRef, useCallback } = React;

const FALLBACK_CROPS = ['Tomato','Potato','Rice','Cotton','Wheat','Maize','Banana','Sugarcane'];

function SevTag({ severity }) {
  const color = severity === 'High' ? 'var(--berry)'
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
      <div className="page-eyebrow" style={{ marginBottom: 8 }}>top matches</div>
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

function PhotoResult({ result, t }) {
  const sevColor = result.severity === 'High' ? 'var(--berry)'
                 : result.severity === 'Medium' ? '#A06B1F'
                 : 'var(--leaf)';
  return (
    <div className="rise">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
        <span className="tag" style={{ color: 'var(--ink-faint)', borderColor: 'var(--line-2)', fontSize: 11 }}>
          via {result.model_used || 'Vision API'}
        </span>
        <SevTag severity={result.severity} />
      </div>
      <div style={{ fontFamily: 'var(--display)', fontSize: 30, color: 'var(--ink)', letterSpacing: '-0.01em', marginTop: 4 }}>
        {result.disease}
      </div>
      {result.action && (
        <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(240,192,96,0.16)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--sun)' }}>right now</div>
          <div style={{ marginTop: 4 }}>{result.action}</div>
        </div>
      )}
      {result.treatment && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>treatment</div>
          <div style={{ marginTop: 4 }}>{result.treatment}</div>
        </div>
      )}
      {result.prevention && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'var(--glass-bg-subtle)', border: '1px solid var(--glass-border)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>prevention</div>
          <div style={{ marginTop: 4 }}>{result.prevention}</div>
        </div>
      )}
      <Top3Bars top3={result.top3} t={t} />
    </div>
  );
}

function PhotoPanel({ t }) {
  const [cropList, setCropList] = useState(null);
  const [cropsLoading, setCropsLoading] = useState(true);
  const [cropType, setCropType] = useState('Tomato');
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  // Fix #5: store chosen file in state so retry doesn't use stale fileRef.current.files
  const [file, setFile] = useState(null);
  const fileRef = useRef();

  useEffect(() => {
    window.api.diseaseCrops()
      .then(data => {
        const names = Object.keys(data);
        setCropList(names.length > 0 ? names : FALLBACK_CROPS);
        setCropType(prev => names.includes(prev) ? prev : names[0] || FALLBACK_CROPS[0]);
      })
      .catch(() => {
        setCropList(FALLBACK_CROPS);
      })
      .finally(() => setCropsLoading(false));
  }, []);

  const analyzeFile = useCallback((f) => {
    if (!f) return;
    setLoading(true);
    setResult(null);
    setError(null);
    window.api.diseasePhoto(f, cropType)
      .then(r => {
        setResult(r);
        setLoading(false);
      })
      .catch(e => {
        setError({
          status: e.status || null,
          detail: e.detail || e.message || String(e),
          message: e.message || String(e),
        });
        setLoading(false);
      });
  }, [cropType]);

  // Fix #6: wrap in useCallback
  const handleFileChange = useCallback((e) => {
    const chosen = e.target.files?.[0];
    if (chosen) {
      setFile(chosen);
      analyzeFile(chosen);
    }
    // reset so same file can be re-selected
    e.target.value = '';
  }, [analyzeFile]);

  // Fix #6: wrap in useCallback
  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDrag(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) {
      setFile(dropped);
      analyzeFile(dropped);
    }
  }, [analyzeFile]);

  function errorMsg(e) {
    if (!e) return 'Something went wrong.';
    if (e.status === 401 || e.status === 403) return 'API key issue — check your config.js setup.';
    if (!e.status && e.message) return 'No connection — check your network and try again.';
    return e.detail || e.message || 'Analysis failed.';
  }

  return (
    <div className="grid-2">
      <div className="card rise rise-1">
        <div className="card-h">
          <h3>Send a photo</h3>
          {cropsLoading ? (
            <span className="muted small" style={{ fontStyle: 'italic' }}>loading crops…</span>
          ) : (
            <select className="input" style={{ width: 140 }} value={cropType} onChange={e => setCropType(e.target.value)}>
              {(cropList || FALLBACK_CROPS).map(c => <option key={c}>{c}</option>)}
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
          <div style={{ marginTop: 10, fontSize: 14 }}><strong>Drop a leaf photo here</strong></div>
          <div className="muted small" style={{ marginTop: 4 }}>or click to choose · jpg, png, webp</div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
        </div>
      </div>

      <div className="card rise rise-2">
        <div className="card-h">
          <h3>What we see</h3>
          {result && <SevTag severity={result.severity} />}
        </div>
        {!loading && !result && !error && (
          <div className="muted" style={{ padding: '30px 0', textAlign: 'center' }}>Send a photo and we'll have a look. 🌿</div>
        )}
        {loading && <Loading label="Analyzing leaf…" />}
        {!loading && error && (
          <ErrorCard
            title="Could not analyze photo"
            detail={errorMsg(error)}
            // Fix #5: retry uses the file stored in state, not stale fileRef.current.files
            onRetry={() => { if (file) analyzeFile(file); }}
          />
        )}
        {!loading && result && <PhotoResult result={result} t={t} />}
      </div>
    </div>
  );
}


function ViewDisease({ profile, t }) {
  return (
    <div className="view-fade">
      <Topbar crumb="Leaf Doctor" />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">leaf doctor</div>
          <h1 className="page-title">A <em>second pair of eyes</em> for sick leaves.</h1>
          <p className="page-lede">Snap a photo of a worried leaf. We'll gently look it over and tell you what's likely going on, with the kindest fix.</p>
        </div>
      </div>

      <PhotoPanel t={t} />
    </div>
  );
}

window.ViewDisease = ViewDisease;
