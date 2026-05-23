// ViewAcoustic — pre-check gate (Task 5.1) + rich result rendering (Task 5.2)
// Form state + API: hooks/useAcousticForm.js
// Display helpers:  hooks/useAcousticDisplayHelpers.js

function ViewAcoustic({ profile, t }) {
  const {
    file, cropType, setCropType,
    drag, setDrag,
    bars,
    audioUrl, inputRef,
    preCheckWarnings, preCheckError,
    loading, error, result,
    analyzeDisabled,
    handleFile, onDrop, clearAll, analyze,
  } = window.useAcousticForm(t);

  return (
    <div className="view-fade">
      <Topbar crumb={t('Listen')} />
      <div className="page-head">
        <div>
          <div className="page-eyebrow">{t('listen')}</div>
          <h1 className="page-title">{t('Hear the bugs')} <em>{t('before they show.')}</em></h1>
          <p className="page-lede">{t("Hold your phone near a plant for a few seconds. We'll listen for the tiny sounds pests make and warn you a week early.")}</p>
        </div>
      </div>

      <div className="grid-2">
        {/* LEFT: Upload card */}
        <div className="card rise rise-1">
          <div className="card-h"><h3>{t('Upload a recording')}</h3><span className="tag">{t('~6 seconds')}</span></div>

          <input
            className="input"
            placeholder={t('Crop type (optional)')}
            value={cropType}
            onChange={e => setCropType(e.target.value)}
            style={{ marginBottom: 12, width: '100%' }}
          />

          <div className="drop"
            onClick={() => inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
            style={{
              borderColor: drag ? 'var(--leaf)' : 'var(--glass-border-strong)',
              background: drag ? 'rgba(127,217,140,0.14)' : 'var(--glass-bg-subtle)',
            }}>
            <div style={{ fontSize: 36 }}>{file ? '🎵' : '🎙'}</div>
            <div style={{ marginTop: 10, fontSize: 14 }}>
              {file ? <strong>{file.name}</strong> : <strong>{t('Drag & drop your field audio here')}</strong>}
            </div>
            <div className="muted small" style={{ marginTop: 4 }}>
              {file
                ? `${(file.size / 1024).toFixed(0)} ${t('KB · ready')}`
                : t('or click to choose · wav · mp3 · m4a · ogg · webm')}
            </div>
            <input ref={inputRef} type="file" accept="audio/*" style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files[0])} />
          </div>

          {file && audioUrl && (
            <audio controls src={audioUrl} style={{ width: '100%', marginTop: 12, borderRadius: 10 }} />
          )}

          {preCheckWarnings.length > 0 && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 12, background: 'rgba(240,192,96,0.14)', border: '1px solid rgba(240,192,96,0.32)' }}>
              {preCheckWarnings.map((w, i) => (
                <div key={i} style={{ fontSize: 13, color: 'var(--sun)', marginBottom: i < preCheckWarnings.length - 1 ? 4 : 0 }}>
                  {t(window.ACOUSTIC_WARNING_LABELS?.[w] || w)}
                </div>
              ))}
            </div>
          )}

          {preCheckError && (
            <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 12, fontSize: 13, border: '1px solid rgba(232,112,95,0.32)', background: 'rgba(232,112,95,0.14)', color: 'var(--berry)' }}>
              {preCheckError}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, gap: 10 }}>
            <div className="muted small" style={{ fontStyle: 'italic' }}>{t('tip: 15–30 cm from the stem · breathe slowly')}</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn" onClick={clearAll}>{t('clear')}</button>
              <button className="btn primary" onClick={analyze} disabled={analyzeDisabled}>
                {loading ? t('🎧 listening…') : t('🔊 analyze')}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT: Result card */}
        <div className="card rise rise-2">
          <div className="card-h">
            <h3>{t('What we heard')}</h3>
            {result && <span className="tag alert">{result.severity}</span>}
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-end', gap: 3, height: 120, padding: '10px 0' }}>
            {bars.map((b, i) => (
              <div key={i} style={{
                width: 5, height: `${Math.max(8, b * 100)}%`,
                background: 'var(--leaf-2)', borderRadius: 2,
                transition: 'height .12s ease',
                opacity: loading ? 0.9 : result ? 0.6 : 0.3,
              }} />
            ))}
          </div>

          {loading && <Loading label={t('Listening to your field…')} />}

          {error && !loading && (
            <ErrorCard t={t} title={t('Analysis failed')} detail={error.message} onRetry={analyze} />
          )}

          {!result && !loading && !error && (
            <div className="muted" style={{ padding: '10px 0', textAlign: 'center' }}>{t('Drop a recording on the left to begin. 🐛')}</div>
          )}

          {result && !loading && <AcousticRichResult r={result} t={t} />}
        </div>
      </div>
    </div>
  );
}

window.ViewAcoustic = ViewAcoustic;
