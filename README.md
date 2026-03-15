# 🌾 Smart Crop Advisory System

> AI-powered decision support for small and marginal farmers in India

## 🔴 Live Demo
👉 [smart-crop-advisor-pryetrqjrna69seh6ne4uq.streamlit.app](https://smart-crop-advisor-pryetrqjrna69seh6ne4uq.streamlit.app)

## Features
| Tab | Feature | Model | Accuracy |
|---|---|---|---|
| 🌾 1 | Crop Recommender | Random Forest | 99.2% |
| 🌿 2 | Disease Detector | MobileNetV2 | 96%+ |
| 💰 3 | Market Price Forecast | Facebook Prophet | 6 crops |
| 💧 4 | Irrigation Advisor | FAO-56 Formula | 22 crops |

## Tech Stack
- **ML Models:** Scikit-learn, TensorFlow/Keras
- **Forecasting:** Facebook Prophet
- **Backend:** Python
- **Frontend:** Streamlit
- **Deployment:** Streamlit Cloud
- **Version Control:** Git, GitHub

## Models
- Random Forest Classifier — 22 crops, soil + climate features
- MobileNetV2 Transfer Learning — 38 plant diseases, 54k images
- Facebook Prophet — 30-day mandi price forecasting
- FAO Penman-Monteith — scientifically validated irrigation formula

## Run Locally
git clone https://github.com/bored-psychic/smart-crop-advisor
cd smart-crop-advisor
pip install -r requirements.txt
streamlit run app.py

## Impact
100M+ small farmers in India make crop decisions with zero data.
This system gives them AI-powered advice via a simple web interface.

## Author
Built by Prajval SB — First Semester CS (AI/ML) Student
