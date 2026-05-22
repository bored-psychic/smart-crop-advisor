// Non-secret runtime config for KisanOS SPA. Copy to config.js.
// The browser no longer holds a shared API key — auth flows through
// phone+OTP and a per-user JWT (see web/lib/api.js + backend /auth/*).
window.API_BASE = "/api";
