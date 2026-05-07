## UI Change Checklist (Streamlit)

Use this before merging UI updates.

- Keep UI styling and business logic changes in separate commits.
- Do not modify API payload/response keys during visual-only passes.
- Smoke-check all tabs after UI edits:
  - Crop recommendation
  - Disease diagnosis (image or symptom)
  - Market forecast
  - Irrigation advice
  - Acoustic analysis
  - Field Watch
- If any API call fails, keep last known UI state and show a user-facing warning.
- Avoid editing legacy `web/` files when working on Streamlit `frontend/`.
