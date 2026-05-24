# Smart Crop Advisory System

> AI-powered decision support for small and marginal farmers in India

## Features
| Feature | Tech / Model | Status |
|---|---|---|
| Crop Recommender | Random Forest (22 crops) | 99.2% Accuracy |
| Disease Detector | TFLite + NumPy HSV Fallback | 96%+ Accuracy |
| Market Price Forecast | Agmarknet API + Prophet | Real-time / Offline |
| Irrigation Advisor | FAO-56 Formula + OWM | 5-min TTL Cached |
| Acoustic Pest Detection | PANNs CNN14 + YAMNet + Gemini/Claude | Active learning |
| Field Watch | NASA FIRMS, Flood & AQI APIs | Graceful degradation |

## Tech Stack
- **Backend:** Python, FastAPI, SQLite, APScheduler
- **ML:** Scikit-learn, TensorFlow/Keras (disease), PyTorch + PANNs (acoustic)
- **Frontend:** Static web UI (`web/`) — vanilla HTML/JS, no build step
- **APIs:** OpenWeatherMap, NASA FIRMS, Agmarknet, Anthropic, Gemini
- **Security:** JWT (HS256), Fernet encryption (PII at rest), peppered hash lookups
- **Deployment:** Docker-ready, Git

## Setup

### Prerequisites
- Python 3.9+
- pip / venv
- 2+ GB free disk (ML models)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/bored-psychic/smart-crop-advisor
cd smart-crop-advisor
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and secrets:
#   - API_KEY: shared secret for internal routes (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
#   - JWT_SECRET: HS256 key for user tokens (generate: python -c "import secrets; print(secrets.token_urlsafe(64))")
#   - APP_PEPPER: pepper for phone hash (generate: python -c "import secrets; print(secrets.token_urlsafe(48))")
#   - FERNET_KEY: encryption key (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
#   - External API keys: OWM_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, NASA_FIRMS_KEY, FAST2SMS_API_KEY, etc.
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the backend API:
```bash
uvicorn backend.main:app --reload
# API runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

7. (Optional) Start the React frontend in a separate terminal:
```bash
cd web && npm install && npm start
```

## Auth Model

The API uses **OTP-based authentication** for end-users and **API key authentication** for service-to-service requests:

- **User authentication (browser):**
  - `POST /auth/request-otp` with phone number → triggers SMS via Fast2SMS
  - `POST /auth/verify-otp` with OTP → returns signed JWT (HS256, 24-hour TTL)
  - Routes protected with `@Depends(require_user)` validate JWT from `Authorization: Bearer` header
  - Phone hashes extracted from JWT claims available to the handler

- **Service-to-service (internal/cron):**
  - Routes protected with `@Depends(require_api_key)` check `X-API-Key` header
  - Used for alert scheduler, admin endpoints

See `backend/auth.py` and `backend/routers/subscriptions.py` for implementation.

## Running Tests

All tests are in `tests/` and use pytest with fixtures for auth tokens:

```bash
pytest                              # Run all tests
pytest -v                           # Verbose output
pytest --cov=backend                # Coverage report
pytest tests/test_crop_router.py    # Run specific test file
```

Key test utilities:
- `tests/conftest.py` exports `auth_token` and `auth_headers` fixtures for authenticated endpoints
- Use `respx` to mock external HTTP calls (OWM, Agmarknet, etc.)

## Project Architecture

For a detailed overview of the router→service→ML data flow, PII encryption, auth flow, and i18n middleware, see [docs/architecture.md](docs/architecture.md).

## Development History

The following audit documents trace security and reliability improvements:

- [P0 Critical](docs/audit/P0-critical.md) — Auth model (OTP+JWT), CORS tightening, rate limiting, secrets hygiene
- [P1 High](docs/audit/P1-high.md) — Error handling, bounded cache, PII encryption at rest, input validation
- [P2 Medium](docs/audit/P2-medium.md) — Security headers, acoustic pipeline refactor, i18n fallback, ML graceful degradation
- [Database Migrations](docs/audit/migrations.md) — Alembic setup and index strategy
- [ML Fallbacks](docs/audit/ml-fallbacks.md) — Offline model loading and degradation paths

## Author

Built by Prajval SB — First Year CS (AI/ML) Student - RNSIT
