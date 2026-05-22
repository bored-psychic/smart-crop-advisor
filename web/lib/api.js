// Centralized API client for KisanOS SPA.
//
// All requests are prefixed with window.API_BASE and carry the per-user
// JWT (issued by /auth/verify-otp) as `Authorization: Bearer <token>`.
// The pre-T3 `X-API-Key` header is gone — the browser no longer holds a
// shared secret.

const TOKEN_KEY = 'kisanos.token';

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ''; }
  catch { return ''; }
}

function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {}
}

// Minimal base64url-JWT payload decoder. Does NOT verify the signature
// (the backend does that); used only to check `exp` client-side and to
// pull `phone` for UI display. Returns null on malformed input.
function decodeJwtPayload(token) {
  if (!token) return null;
  const parts = String(token).split('.');
  if (parts.length !== 3) return null;
  try {
    let b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    while (b64.length % 4) b64 += '=';
    const json = atob(b64);
    return JSON.parse(decodeURIComponent(escape(json)));
  } catch {
    return null;
  }
}

function isTokenValid(token) {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return false;
  return payload.exp * 1000 > Date.now();
}

class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function _req(path, opts = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (window.__lang) headers['Accept-Language'] = window.__lang;

  let body;
  if (opts.formData) {
    // FormData: let browser set Content-Type with multipart boundary
    body = opts.formData;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }

  const fetchOpts = {
    method: opts.method || 'GET',
    headers,
  };
  if (body !== undefined) {
    fetchOpts.body = body;
  }

  let r;
  try {
    r = await fetch(`${window.API_BASE}${path}`, fetchOpts);
  } catch (err) {
    err.message = `${path}: ${err.message}`;
    throw err;
  }

  // 401 anywhere means the token is gone/expired — drop it so the SPA
  // re-routes to Login on next render.
  if (r.status === 401) {
    setToken('');
    window.dispatchEvent(new CustomEvent('kisanos:auth-expired'));
  }

  if (!r.ok) {
    let detail;
    try {
      const json = await r.json();
      detail = json.detail || r.statusText;
    } catch (_) {
      detail = r.statusText;
    }
    throw new ApiError(r.status, detail);
  }

  return r.json();
}

window.api = {
  // ── Auth ─────────────────────────────────────────────────────────
  authRequestOtp: (phone) => _req('/auth/request-otp', { method: 'POST', body: { phone } }),
  authVerifyOtp:  (phone, otp) => _req('/auth/verify-otp',  { method: 'POST', body: { phone, otp } }),
  authMe:         () => _req('/auth/me'),

  // ── Domain endpoints ─────────────────────────────────────────────
  cropRecommend: (body) => _req('/crop/recommend', { method: 'POST', body }),

  diseaseTreatmentPrice: (body) => _req('/disease/treatment-price', { method: 'POST', body }),

  diseasePhoto: (file, crop_type) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('crop_type', crop_type);
    return _req('/disease/analyze-image', { method: 'POST', formData: fd });
  },

  diseaseSymptom: (crop, symptom) =>
    _req('/disease/analyze-symptom', { method: 'POST', body: { crop, symptom } }),

  diseaseCrops: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return _req('/disease/crops' + (qs ? '?' + qs : ''));
  },

  marketForecast: (crop, city, forecast_days) =>
    _req('/market/forecast', { method: 'POST', body: { crop, city, forecast_days } }),

  irrigationAdvise: (body) => _req('/irrigation/advise', { method: 'POST', body }),

  acousticAnalyze: (file, crop_type) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('crop_type', crop_type);
    return _req('/acoustic/analyze', { method: 'POST', formData: fd });
  },

  fieldWatchScan: (city) => _req('/field-watch/scan', { method: 'POST', body: { city } }),

  soilAnalyze: (body) => _req('/soil/analyze', { method: 'POST', body }),

  dosageRecommend: (body) => _req('/dosage/recommend', { method: 'POST', body }),

  alertsSubscribe:     (body) => _req('/alerts/subscribe',        { method: 'POST', body }),
  alertsUnsubscribe:   (id)   => _req(`/alerts/unsubscribe/${id}`, { method: 'DELETE' }),
  alertsHistory:       (phone)=> _req(`/alerts/history?phone=${encodeURIComponent(phone)}`),
  alertsPushSubscribe: (body) => _req('/alerts/push-subscribe',   { method: 'POST', body }),
  alertsVapidKey:      ()     => _req('/alerts/vapid-public-key'),
};

window.ApiError = ApiError;

// Exposed helpers for components — token CRUD and JWT decode in one place.
window.auth = {
  getToken,
  setToken,
  clearToken: () => setToken(''),
  decodeJwtPayload,
  isTokenValid,
};
