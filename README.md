# 🌾 Smart Crop Advisory System

> AI-powered decision support for small and marginal farmers in India

## 🔴 Live Demo
👉 [smart-crop-advisor-pryetrqjrna69seh6ne4uq.streamlit.app](https://smart-crop-advisor-pryetrqjrna69seh6ne4uq.streamlit.app)

## Features
| Tab | Feature | Tech / Model | Status / Metric |
|---|---|---|---|
| 🌾 1 | Crop Recommender | Random Forest | 99.2% Accuracy |
| 🌿 2 | Disease Detector | MobileNetV2 + NumPy HSV Fallback | 96%+ / 0.01ms Inference |
| 💰 3 | Market Price Forecast | Agmarknet API + Prophet Fallback | Real-time / Offline |
| 💧 4 | Irrigation Advisor | FAO-56 Formula + OWM API | 5-min TTL Cached |
| 🎙️ 5 | Acoustic Analysis | Pest/Stress Audio Detection | Active |
| 🛰️ 6 | Field Watch | NASA FIRMS, Flood & AQI APIs | Graceful Degradation |

## Tech Stack
- **ML Models:** Scikit-learn, TensorFlow/Keras
- **Forecasting:** Facebook Prophet
- **Backend / Core:** Python, FastAPI (Decoupled), NumPy (Vectorization)
- **Frontend:** Streamlit (KisanOS Swarm UI)
- **APIs:** OpenWeatherMap, NASA FIRMS, Agmarknet
- **Deployment & Version Control:** Streamlit Cloud, Git, GitHub

## Models & Architecture
- **Random Forest Classifier** — 22 crops, soil + climate features
- **MobileNetV2 Transfer Learning** — 38 plant diseases, 54k images
- **Vectorized HSV Fallback** — High-speed, dependency-free NumPy image processing avoiding heavy TF imports
- **Facebook Prophet** — 30-day mandi price forecasting with automatic offline fallback
- **FAO Penman-Monteith** — Scientifically validated irrigation formula
- **Modular Swarm Architecture** — Decoupled UI (`frontend/`) and logic (`backend/`) with strict API fault tolerance and module-level caching.

## Impact
100M+ small farmers in India make crop decisions with zero data.
This system gives them AI-powered advice via a simple web interface.

## Author
Built by Prajval SB — First Year CS (AI/ML) Student - RNSIT

## Run Locally

```bash
git clone [https://github.com/bored-psychic/smart-crop-advisor](https://github.com/bored-psychic/smart-crop-advisor)
cd smart-crop-advisor
pip install -r requirements.txt
PYTHONPATH=. streamlit run frontend/app.py


