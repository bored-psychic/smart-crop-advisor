// Acoustic display helpers: roleColor, MethodBadge, TopBars, BandChart, RichResult
// Used only by ViewAcoustic — extracted to keep the view file under 250 lines.

function roleColor(role) {
  if (role === 'pest')       return 'var(--berry)';
  if (role === 'pollinator') return 'var(--leaf)';
  if (role === 'vector')     return 'var(--sun)';
  return 'var(--ink-faint)';
}

function AcousticMethodBadge({ method }) {
  if (!method) return null;
  const goodMethods = ['yamnet', 'claude_vision', 'gemini_audio'];
  const color = goodMethods.includes(method) ? 'var(--leaf)' : 'var(--berry)';
  return (
    <span style={{
      display: 'inline-block', fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
      textTransform: 'uppercase', padding: '3px 9px', borderRadius: 999,
      background: color, color: '#fff', marginBottom: 12,
    }}>{method.replace(/_/g, ' ')}</span>
  );
}

function AcousticTopBars({ top3, t }) {
  if (!top3 || !top3.length) return null;
  const maxVal = Math.max(...top3.map(([, p]) => p), 1);
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: 8 }}>{t('top detections')}</div>
      {top3.map(([name, pct], i) => (
        <div key={i} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
            <span>{name}</span><span style={{ color: 'var(--ink-soft)' }}>{Math.round(pct)}%</span>
          </div>
          <div style={{ height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.10)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(pct / maxVal) * 100}%`, background: 'var(--leaf)', borderRadius: 4, transition: 'width 0.8s ease' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function AcousticBandChart({ bandEnergy, t }) {
  if (!bandEnergy || !Object.keys(bandEnergy).length) return null;
  const entries = Object.entries(bandEnergy);
  const maxVal  = Math.max(...entries.map(([, v]) => v), 0.001);
  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginBottom: 8 }}>{t('band energy')}</div>
      {entries.map(([band, val], i) => (
        <div key={i} style={{ marginBottom: 7 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
            <span style={{ color: 'var(--ink-soft)' }}>{band}</span>
            <span style={{ color: 'var(--ink-faint)' }}>{val.toFixed ? val.toFixed(4) : val}</span>
          </div>
          <div style={{ height: 7, borderRadius: 4, background: 'rgba(255,255,255,0.10)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(val / maxVal) * 100}%`, background: 'var(--leaf)', borderRadius: 4 }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function AcousticRichResult({ r, t }) {
  const rc = roleColor(r.role);
  return (
    <div className="rise">
      <AcousticMethodBadge method={r.analysis_method} />
      <div style={{
        padding: '16px 18px', borderRadius: 14, marginBottom: 14, border: `2px solid ${rc}`,
        background: r.role === 'pest' ? 'rgba(232,112,95,0.14)' : r.role === 'pollinator' ? 'var(--leaf-soft)' : 'var(--glass-bg)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
          <span style={{ fontSize: 36 }}>{r.icon || '🐛'}</span>
          <div style={{ fontFamily: 'var(--display)', fontSize: 32, color: rc, lineHeight: 1 }}>{r.pest}</div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 9px', borderRadius: 999, background: rc, color: '#fff' }}>{r.role}</span>
          {r.severity && (
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 9px', borderRadius: 999, background: 'rgba(255,255,255,0.10)', color: 'var(--ink-soft)' }}>{r.severity}</span>
          )}
        </div>
        {r.action && (
          <div style={{ padding: '10px 13px', borderRadius: 10, fontSize: 14, lineHeight: 1.5, background: 'rgba(255,255,255,0.08)', color: r.role === 'ambient' || r.is_pest === false ? 'var(--ink-soft)' : 'var(--ink)' }}>{r.action}</div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginBottom: 14 }}>
        {[
          { label: t('Confidence'), value: `${Math.round(r.confidence || 0)}%` },
          { label: t('Duration'),   value: `${r.analyzed_seconds || 0}s / ${r.duration_seconds || 0}s` },
          { label: t('Sample rate'), value: `${r.sample_rate || 0} Hz` },
          { label: t('Energy'),     value: r.energy_level || '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{ padding: '10px 12px', borderRadius: 12, background: 'var(--glass-bg-subtle)', border: '1px solid var(--glass-border)', textAlign: 'center' }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)', fontFamily: 'var(--display)' }}>{value}</div>
            <div style={{ fontSize: 10, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--ink-faint)', marginTop: 3 }}>{label}</div>
          </div>
        ))}
      </div>

      <AcousticTopBars top3={r.top3} t={t} />

      {r.claude_advice && (
        <div style={{ marginTop: 16, padding: '12px 16px', borderRadius: 12, background: 'var(--leaf-soft)', borderLeft: '3px solid var(--leaf)', fontSize: 14, lineHeight: 1.6, color: 'var(--ink)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--leaf)', marginBottom: 6, fontWeight: 600 }}>{t('Claude advice')}</div>
          {r.claude_advice}
        </div>
      )}

      {r.quality_warnings && r.quality_warnings.length > 0 && (
        <div style={{ marginTop: 14, padding: '10px 14px', borderRadius: 12, background: 'rgba(240,192,96,0.14)', border: '1px solid rgba(240,192,96,0.32)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--sun)', marginBottom: 6, fontWeight: 600 }}>{t('quality notes')}</div>
          {r.quality_warnings.map((w, i) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--sun)', marginBottom: 3 }}>{t(window.ACOUSTIC_WARNING_LABELS?.[w] || w)}</div>
          ))}
        </div>
      )}

      <AcousticBandChart bandEnergy={r.band_energy} t={t} />

      {r.methodology_note && (
        <div style={{ marginTop: 14, fontSize: 12, color: 'var(--ink-faint)', fontStyle: 'italic', lineHeight: 1.5 }}>{r.methodology_note}</div>
      )}

      <details style={{ marginTop: 18 }}>
        <summary style={{ cursor: 'pointer', fontSize: 13, color: 'var(--ink-soft)', userSelect: 'none' }}>
          {t('Reference library')} ({Object.keys(window.PEST_META || {}).length} {t('known insects')})
        </summary>
        <div style={{ marginTop: 10, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line-2)' }}>
                {['Icon', 'Name', 'Role', 'Severity', 'Freq range'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--ink-faint)', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', fontSize: 10 }}>{t(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(window.PEST_META || {}).map(([name, meta]) => (
                <tr key={name} style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <td style={{ padding: '5px 8px', fontSize: 18 }}>{meta.icon}</td>
                  <td style={{ padding: '5px 8px' }}>{name}</td>
                  <td style={{ padding: '5px 8px', color: roleColor(meta.role) }}>{t(meta.roleLabel)}</td>
                  <td style={{ padding: '5px 8px', color: 'var(--ink-soft)', textTransform: 'capitalize' }}>{meta.severity}</td>
                  <td style={{ padding: '5px 8px', color: 'var(--ink-faint)' }}>{(r.pest === name && r.freq_range) ? r.freq_range : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

window.roleColor          = roleColor;
window.AcousticRichResult = AcousticRichResult;
