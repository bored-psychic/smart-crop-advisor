// Auth screen — two-step phone+OTP flow.
//
// Step 1: user enters phone, we POST /auth/request-otp. On 2xx we move
//         to step 2.
// Step 2: user enters the 6-digit code, we POST /auth/verify-otp; on
//         2xx we stash the returned JWT via window.auth.setToken and
//         call onSignIn so app.jsx flips into the authenticated view.
const { useState: useStateLogin } = React;

function Login({ onSignIn, t }) {
  const tr = t || ((k) => k);
  const [step, setStep] = useStateLogin('phone'); // 'phone' | 'otp'
  const [phone, setPhone] = useStateLogin('');
  // The server normalises the phone (e.g. adds +91) — we keep the
  // canonical form returned from request-otp so verify-otp uses the
  // exact same key.
  const [normalisedPhone, setNormalisedPhone] = useStateLogin('');
  const [otp, setOtp] = useStateLogin('');
  const [error, setError] = useStateLogin('');
  const [busy, setBusy] = useStateLogin(false);
  const [info, setInfo] = useStateLogin('');
  // Set only when the server returns demo_otp (Fast2SMS disabled). The
  // SPA shows the code on screen instead of requiring SMS delivery.
  const [demoOtp, setDemoOtp] = useStateLogin('');

  function validatePhone() {
    const digits = phone.replace(/\D/g, '');
    if (digits.length < 10) return tr('Enter a valid mobile number');
    return '';
  }

  function validateOtp() {
    const digits = otp.replace(/\D/g, '');
    if (digits.length < 4 || digits.length > 8) return tr('Enter the code you received');
    return '';
  }

  async function submitPhone(e) {
    e.preventDefault();
    const err = validatePhone();
    if (err) { setError(err); return; }
    setError(''); setInfo(''); setBusy(true);
    try {
      const resp = await window.api.authRequestOtp(phone.trim());
      setNormalisedPhone(resp.phone || phone.trim());
      setDemoOtp(resp.demo_otp || '');
      setStep('otp');
      setInfo(resp.demo_otp ? '' : tr('Code sent. Check your phone.'));
    } catch (ex) {
      setError(ex.detail || ex.message || tr('Could not send code. Try again.'));
    } finally {
      setBusy(false);
    }
  }

  async function submitOtp(e) {
    e.preventDefault();
    const err = validateOtp();
    if (err) { setError(err); return; }
    setError(''); setBusy(true);
    try {
      const resp = await window.api.authVerifyOtp(normalisedPhone, otp.trim());
      window.auth.setToken(resp.token);
      onSignIn && onSignIn({ phone: resp.phone });
    } catch (ex) {
      setError(ex.detail || ex.message || tr('Invalid or expired code.'));
    } finally {
      setBusy(false);
    }
  }

  function backToPhone() {
    setStep('phone');
    setOtp('');
    setError('');
    setInfo('');
  }

  async function resend() {
    if (busy) return;
    setError(''); setInfo(''); setBusy(true);
    try {
      const resp = await window.api.authRequestOtp(normalisedPhone || phone.trim());
      setNormalisedPhone(resp.phone || normalisedPhone);
      setDemoOtp(resp.demo_otp || '');
      setInfo(resp.demo_otp ? '' : tr('Code resent.'));
    } catch (ex) {
      setError(ex.detail || ex.message || tr('Could not resend code.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={step === 'phone' ? submitPhone : submitOtp} noValidate>
        <div className="auth-brand">
          <span className="leaf-dot" aria-hidden="true" />
          <span className="name">{tr('Kisan')}<em>{tr('OS')}</em></span>
        </div>
        <h1 className="auth-title">{tr('Welcome back')}</h1>
        <p className="auth-sub">
          {step === 'phone'
            ? tr('Sign in to your farm dashboard.')
            : tr('Enter the code we sent to your phone.')}
        </p>

        {step === 'phone' ? (
          <div className="auth-field">
            <label htmlFor="auth-id">{tr('Mobile number')}</label>
            <input id="auth-id"
                   className="auth-input"
                   type="tel"
                   inputMode="tel"
                   autoComplete="tel"
                   placeholder="+91 98765 43210"
                   value={phone}
                   onChange={(e) => setPhone(e.target.value)} />
          </div>
        ) : (
          <>
            <div className="auth-field">
              <label htmlFor="auth-id">{tr('Mobile number')}</label>
              <input id="auth-id"
                     className="auth-input"
                     type="tel"
                     value={normalisedPhone}
                     readOnly />
            </div>
            {demoOtp && (
              <div
                role="status"
                style={{
                  margin: '4px 0 14px',
                  padding: '10px 14px',
                  borderRadius: 12,
                  background: 'rgba(127,217,140,0.10)',
                  border: '1px solid rgba(127,217,140,0.42)',
                  color: 'var(--ink)',
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 12,
                }}>
                <span style={{ color: 'var(--ink-soft)' }}>
                  {tr('Demo mode — your code:')}
                </span>
                <button
                  type="button"
                  onClick={() => setOtp(demoOtp)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--leaf)',
                    fontFamily: 'var(--display)',
                    fontSize: 22,
                    fontWeight: 500,
                    letterSpacing: '0.18em',
                    padding: '0 4px',
                  }}
                  title={tr('Tap to fill')}>
                  {demoOtp}
                </button>
              </div>
            )}
            <div className="auth-field">
              <label htmlFor="auth-otp">{tr('Verification code')}</label>
              <input id="auth-otp"
                     className="auth-input"
                     type="text"
                     inputMode="numeric"
                     autoComplete="one-time-code"
                     pattern="\d*"
                     maxLength={8}
                     placeholder="123456"
                     value={otp}
                     onChange={(e) => setOtp(e.target.value)} />
            </div>
          </>
        )}

        {error && <div className="auth-error" role="alert">{error}</div>}
        {!error && info && <div className="auth-info" role="status">{info}</div>}

        <button type="submit" className="auth-submit" disabled={busy}>
          {busy
            ? (step === 'phone' ? tr('Sending…') : tr('Verifying…'))
            : (step === 'phone' ? tr('Send code') : tr('Sign in'))}
        </button>

        {step === 'otp' && (
          <div className="auth-row">
            <a className="auth-link" href="#"
               onClick={(e) => { e.preventDefault(); backToPhone(); }}>
              {tr('Change number')}
            </a>
            <a className="auth-link" href="#"
               onClick={(e) => { e.preventDefault(); resend(); }}>
              {tr('Resend code')}
            </a>
          </div>
        )}

        <div className="auth-divider">{tr('OR')}</div>
        <p className="auth-foot">
          {tr('Your phone number is your KisanOS identity.')}
        </p>
      </form>
    </div>
  );
}

window.Login = Login;
