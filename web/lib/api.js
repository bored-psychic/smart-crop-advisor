// Centralized API client for KisanOS SPA
// All requests inject X-API-Key from window.API_KEY and are prefixed with window.API_BASE

class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function _req(path, opts = {}) {
  const headers = { 'X-API-Key': window.API_KEY };

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

  const r = await fetch(`${window.API_BASE}${path}`, fetchOpts);

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
  cropRecommend: (body) => _req('/crop/recommend', { method: 'POST', body }),

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

  marketForecast: (crop, state, forecast_days) =>
    _req('/market/forecast', { method: 'POST', body: { crop, state, forecast_days } }),

  irrigationAdvise: (body) => _req('/irrigation/advise', { method: 'POST', body }),

  acousticAnalyze: (file, crop_type) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('crop_type', crop_type);
    return _req('/acoustic/analyze', { method: 'POST', formData: fd });
  },

  fieldWatchScan: (city) => _req('/field-watch/scan', { method: 'POST', body: { city } }),
};

window.ApiError = ApiError;
