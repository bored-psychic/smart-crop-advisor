// ViewDisease — photo + symptom flows with real API
const { useState, useEffect, useRef, useMemo, useCallback } = React;

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

function Top3Bars({ top3 }) {
  if (!top3 || top3.length === 0) return null;
  const max = top3[0]?.[1] || 1;
  return (
    <div style={{ marginTop: 14 }}>
      <div className="page-eyebrow" style={{ marginBottom: 8 }}>top matches</div>
      {top3.map(([name, pct]) => (
        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <div style={{ width: 120, fontSize: 12, color: 'var(--ink-soft)', textAlign: 'right' }}>{name}</div>
          <div style={{ flex: 1, height: 6, background: 'rgba(42,51,40,0.08)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ width: `${(pct / max) * 100}%`, height: '100%', background: 'var(--leaf)', borderRadius: 99, transition: 'width 0.8s ease' }} />
          </div>
          <div style={{ width: 40, fontSize: 12, color: 'var(--ink-faint)', textAlign: 'right' }}>{pct}%</div>
        </div>
      ))}
    </div>
  );
}

function PhotoResult({ result }) {
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
        <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(217,182,107,0.18)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: '#A06B1F' }}>right now</div>
          <div style={{ marginTop: 4 }}>{result.action}</div>
        </div>
      )}
      {result.treatment && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'rgba(199,214,189,0.4)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>treatment</div>
          <div style={{ marginTop: 4 }}>{result.treatment}</div>
        </div>
      )}
      {result.prevention && (
        <div style={{ marginTop: 10, padding: '12px 14px', background: 'rgba(199,214,189,0.15)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>prevention</div>
          <div style={{ marginTop: 4 }}>{result.prevention}</div>
        </div>
      )}
      <Top3Bars top3={result.top3} />
    </div>
  );
}

function SymptomResult({ result }) {
  return (
    <div className="card rise" style={{ marginTop: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
        <div style={{ fontFamily: 'var(--display)', fontSize: 26, color: 'var(--ink)' }}>{result.disease}</div>
        {result.disease_type && (
          <span className="tag">{result.disease_type}</span>
        )}
        {result.severity && <SevTag severity={result.severity} />}
      </div>
      {result.treatment && (
        <div style={{ padding: '12px 14px', background: 'rgba(199,214,189,0.4)', borderRadius: 12, marginBottom: 10 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>treatment</div>
          <div style={{ marginTop: 4 }}>{result.treatment}</div>
        </div>
      )}
      {result.prevention && (
        <div style={{ padding: '12px 14px', background: 'rgba(199,214,189,0.15)', borderRadius: 12 }}>
          <div className="page-eyebrow" style={{ color: 'var(--leaf)' }}>prevention</div>
          <div style={{ marginTop: 4 }}>{result.prevention}</div>
        </div>
      )}
    </div>
  );
}

function PhotoPanel() {
  const [cropList, setCropList] = useState(null);
  const [cropsLoading, setCropsLoading] = useState(true);
  const [cropType, setCropType] = useState('Tomato');
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
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

  const analyzeFile = useCallback((file) => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    setError(null);
    window.__catMood?.('thinking', 2500);
    window.api.diseasePhoto(file, cropType)
      .then(r => {
        setResult(r);
        setLoading(false);
        window.__catMood?.('excited', 1500);
      })
      .catch(e => {
        setError(e);
        setLoading(false);
      });
  }, [cropType]);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file) analyzeFile(file);
    // reset so same file can be re-selected
    e.target.value = '';
  }

  function onDrop(e) {
    e.preventDefault();
    setDrag(false);
    const file = e.dataTransfer.files?.[0];
    if (file) analyzeFile(file);
  }

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
            borderColor: drag ? 'var(--leaf)' : 'var(--line-2)',
            background: drag ? 'rgba(199,214,189,0.4)' : 'rgba(255,255,255,0.4)',
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
        <div style={{ display: 'flex', gap: 10, marginTop: 14 }}>
          <button className="btn ghost">📸 Use camera</button>
          <button className="btn ghost">🔊 Read aloud</button>
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
            onRetry={() => {
              if (fileRef.current?.files?.[0]) analyzeFile(fileRef.current.files[0]);
            }}
          />
        )}
        {!loading && result && <PhotoResult result={result} />}
      </div>
    </div>
  );
}

function SymptomPanel() {
  const cropsRef = useRef(null);
  const [cropsLoading, setCropsLoading] = useState(false);
  const [cropsError, setCropsError] = useState(null);
  const [cropList, setCropList] = useState([]);
  const [selectedCrop, setSelectedCrop] = useState('');
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  // Lazy-load detailed crops on first mount of this panel
  useEffect(() => {
    if (cropsRef.current) {
      // Already fetched
      setCropList(Object.keys(cropsRef.current));
      return;
    }
    setCropsLoading(true);
    setCropsError(null);
    window.api.diseaseCrops({ detailed: true })
      .then(data => {
        cropsRef.current = data;
        const names = Object.keys(data);
        setCropList(names);
        setSelectedCrop(names[0] || '');
        setCropsLoading(false);
      })
      .catch(e => {
        setCropsError(e);
        setCropsLoading(false);
      });
  }, []);

  const symptoms = useMemo(() => {
    if (!cropsRef.current || !selectedCrop) return [];
    return cropsRef.current[selectedCrop] || [];
  }, [selectedCrop, cropList]);

  function handleSymptomClick(item) {
    setAnalysisLoading(true);
    setAnalysisResult(null);
    setAnalysisError(null);
    window.__catMood?.('thinking', 2000);
    window.api.diseaseSymptom(selectedCrop, item.symptom)
      .then(r => {
        setAnalysisResult(r);
        setAnalysisLoading(false);
        window.__catMood?.('excited', 1500);
      })
      .catch(e => {
        setAnalysisError(e);
        setAnalysisLoading(false);
      });
  }

  function symptomErrMsg(e) {
    if (!e) return 'Something went wrong.';
    if (e.status === 401 || e.status === 403) return 'API key issue — check your config.js setup.';
    if (!e.status && e.message) return 'No connection — check your network and try again.';
    return e.detail || e.message || 'Lookup failed.';
  }

  const sevColor = (sev) =>
    sev === 'High' ? 'var(--berry)' : sev === 'Medium' ? '#A06B1F' : 'var(--leaf)';

  if (cropsLoading) {
    return <Loading label="Loading symptom library…" />;
  }

  if (cropsError) {
    return (
      <ErrorCard
        title="Could not load symptoms"
        detail={symptomErrMsg(cropsError)}
        onRetry={() => {
          cropsRef.current = null;
          setCropsError(null);
          setCropsLoading(true);
          window.api.diseaseCrops({ detailed: true })
            .then(data => {
              cropsRef.current = data;
              const names = Object.keys(data);
              setCropList(names);
              setSelectedCrop(names[0] || '');
              setCropsLoading(false);
            })
            .catch(e => { setCropsError(e); setCropsLoading(false); });
        }}
      />
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--ink-soft)', fontWeight: 500 }}>Crop</label>
        <select
          className="input"
          style={{ width: 180 }}
          value={selectedCrop}
          onChange={e => {
            setSelectedCrop(e.target.value);
            setAnalysisResult(null);
            setAnalysisError(null);
          }}
        >
          {cropList.map(c => <option key={c}>{c}</option>)}
        </select>
      </div>

      {symptoms.length === 0 && (
        <div className="muted" style={{ padding: '24px 0', textAlign: 'center' }}>No symptoms found for this crop.</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12 }}>
        {symptoms.map((item, i) => (
          <button
            key={i}
            className="tile"
            style={{ textAlign: 'left', padding: '12px 14px', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 6 }}
            onClick={() => handleSymptomClick(item)}
          >
            <div style={{ fontSize: 13, color: 'var(--ink)', lineHeight: 1.5 }}>{item.symptom}</div>
            {item.severity && (
              <span
                className="tag"
                style={{
                  fontSize: 11,
                  color: sevColor(item.severity),
                  borderColor: sevColor(item.severity) + '40',
                  background: sevColor(item.severity) + '14',
                  alignSelf: 'flex-start',
                }}
              >
                {item.severity}
              </span>
            )}
          </button>
        ))}
      </div>

      {analysisLoading && (
        <div style={{ marginTop: 18 }}>
          <Loading label="Looking up disease…" />
        </div>
      )}
      {!analysisLoading && analysisError && (
        <div style={{ marginTop: 18 }}>
          <ErrorCard title="Could not analyze symptom" detail={symptomErrMsg(analysisError)} />
        </div>
      )}
      {!analysisLoading && analysisResult && (
        <SymptomResult result={analysisResult} />
      )}
    </div>
  );
}

function ViewDisease({ profile, t }) {
  const [method, setMethod] = useState('photo');
  const [symptomMounted, setSymptomMounted] = useState(false);

  function switchMethod(m) {
    setMethod(m);
    if (m === 'symptom') setSymptomMounted(true);
  }

  return (
    <div className="view-fade">
      <Topbar crumb="Leaf Doctor" />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">leaf doctor</div>
          <h1 className="page-title">A <em>second pair of eyes</em> for sick leaves.</h1>
          <p className="page-lede">Snap a photo of a worried leaf, or describe what you see. We'll gently look it over and tell you what's likely going on, with the kindest fix.</p>
        </div>
      </div>

      {/* Method toggle */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        <button
          className={method === 'photo' ? 'btn primary' : 'btn ghost'}
          onClick={() => switchMethod('photo')}
        >
          📷 Photo
        </button>
        <button
          className={method === 'symptom' ? 'btn primary' : 'btn ghost'}
          onClick={() => switchMethod('symptom')}
        >
          📋 Describe symptoms
        </button>
      </div>

      {method === 'photo' && <PhotoPanel />}

      {symptomMounted && (
        <div style={{ display: method === 'symptom' ? 'block' : 'none' }}>
          <SymptomPanel />
        </div>
      )}
    </div>
  );
}

window.ViewDisease = ViewDisease;
