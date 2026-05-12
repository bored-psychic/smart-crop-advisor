// Auth screen — glass card over field photography
const { useState: useStateLogin } = React;

function Login({ onSignIn, t }) {
  const tr = t || ((k) => k);
  const [mode, setMode] = useStateLogin('email');
  const [identifier, setIdentifier] = useStateLogin('');
  const [password, setPassword] = useStateLogin('');
  const [showPw, setShowPw] = useStateLogin(false);
  const [remember, setRemember] = useStateLogin(true);
  const [error, setError] = useStateLogin('');
  const [busy, setBusy] = useStateLogin(false);

  function validate() {
    if (!identifier.trim()) return mode === 'email' ? 'Enter your email' : 'Enter your mobile number';
    if (mode === 'email') {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier.trim())) return 'Enter a valid email address';
    } else {
      const digits = identifier.replace(/\D/g, '');
      if (digits.length < 10) return 'Enter a valid mobile number';
    }
    if (password.length < 6) return 'Password must be at least 6 characters';
    return '';
  }

  function submit(e) {
    e.preventDefault();
    const err = validate();
    if (err) { setError(err); return; }
    setError('');
    setBusy(true);
    setTimeout(() => {
      setBusy(false);
      onSignIn && onSignIn({ mode, identifier: identifier.trim(), remember });
    }, 480);
  }

  function switchMode(next) {
    if (next === mode) return;
    setMode(next);
    setIdentifier('');
    setError('');
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit} noValidate>
        <div className="auth-brand">
          <span className="leaf-dot" aria-hidden="true" />
          <span className="name">Kisan<em>OS</em></span>
        </div>
        <h1 className="auth-title">{tr('Welcome back')}</h1>
        <p className="auth-sub">{tr('Sign in to your farm dashboard.')}</p>

        <div className="auth-tabs" role="tablist" aria-label="Sign in method">
          <button type="button" role="tab" aria-selected={mode === 'email'}
                  className={mode === 'email' ? 'active' : ''}
                  onClick={() => switchMode('email')}>
            {tr('Email')}
          </button>
          <button type="button" role="tab" aria-selected={mode === 'mobile'}
                  className={mode === 'mobile' ? 'active' : ''}
                  onClick={() => switchMode('mobile')}>
            {tr('Mobile')}
          </button>
        </div>

        <div className="auth-field">
          <label htmlFor="auth-id">{mode === 'email' ? tr('Email address') : tr('Mobile number')}</label>
          <input id="auth-id"
                 className="auth-input"
                 type={mode === 'email' ? 'email' : 'tel'}
                 inputMode={mode === 'email' ? 'email' : 'tel'}
                 autoComplete={mode === 'email' ? 'email' : 'tel'}
                 placeholder={mode === 'email' ? 'ramesh@example.com' : '+91 98765 43210'}
                 value={identifier}
                 onChange={(e) => setIdentifier(e.target.value)} />
        </div>

        <div className="auth-field">
          <label htmlFor="auth-pw">{tr('Password')}</label>
          <input id="auth-pw"
                 className="auth-input has-trailing"
                 type={showPw ? 'text' : 'password'}
                 autoComplete="current-password"
                 placeholder="••••••••"
                 value={password}
                 onChange={(e) => setPassword(e.target.value)} />
          <button type="button" className="auth-eye"
                  aria-label={showPw ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPw(s => !s)}>
            {showPw ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3l18 18" />
                <path d="M10.6 6.2A10 10 0 0 1 12 6c5 0 9 4 10 6-0.5 1-1.6 2.6-3.3 4M6.4 6.5C4 8 2.5 10 2 12c1 2 5 6 10 6 1.5 0 2.9-.3 4.1-.9" />
                <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            )}
          </button>
        </div>

        {error && <div className="auth-error" role="alert">{error}</div>}

        <div className="auth-row">
          <label className="auth-check">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
            {tr('Remember me')}
          </label>
          <a className="auth-link" href="#" onClick={(e) => e.preventDefault()}>{tr('Forgot password?')}</a>
        </div>

        <button type="submit" className="auth-submit" disabled={busy}>
          {busy ? tr('Signing in…') : tr('Sign in')}
        </button>

        <div className="auth-divider">{tr('OR')}</div>
        <p className="auth-foot">
          {tr("New to KisanOS?")} <a href="#" onClick={(e) => e.preventDefault()}>{tr('Create an account')}</a>
        </p>
      </form>
    </div>
  );
}

window.Login = Login;
