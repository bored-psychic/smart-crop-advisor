# P3 — Low Severity / Polish (Smart Crop Advisor)

> **For the executing sub-agent**: Self-contained brief. These are
> tech-debt cleanups, not bug fixes. Do P0/P1/P2 first. Each task here is
> independent and safe to parallelize.

## Project context

Polish items: unpinned and bloated dependency stack, an oversized
Streamlit god file, hardcoded geographic data on the client, a PRAGMA
f-string code smell, and oversized React view components. None of these
is dangerous today, but each will slow down anyone trying to refactor
or deploy.

---

## Task 1 — Pin and slim `requirements.txt`

**Scope**: `requirements.txt`, possibly new `requirements-dev.txt`.

**Steps**:

1. Pin every line to an exact version. Use the currently-installed
   versions: `pip freeze > requirements.txt`, then review for stragglers
   and adjust.
2. Split:
   - `requirements.txt` (or `requirements-prod.txt`) → runtime only.
   - `requirements-dev.txt` → `pytest`, `pytest-cov`, `respx`,
     `pytest-asyncio`, `ruff`, anything else dev-only.
3. Review for duplication: TF, PyTorch, librosa, pydub, pyloudnorm,
   panns_inference, tensorflow_hub. If only one acoustic backend is in
   live use after the P2 acoustic split, drop the rest. **Confirm with
   user before removing any backend** — this is a product decision.
4. Lazy-import the heavy ML modules inside the pipeline functions so
   startup doesn't load all three.

**Verification**:
- `pip install -r requirements.txt` on a fresh venv reproduces the lock.
- `python -c "import backend.main"` boot time drops noticeably (compare
  `time` before/after).
- `pytest` green.

---

## Task 2 — Slim `frontend/app.py`

**Scope**: `frontend/app.py` (632 lines).

**Steps**:

1. Move all CSS strings to `frontend/styles.py` (or a `.css` file loaded
   via `st.markdown`).
2. Move sidebar config to `frontend/sidebar.py`.
3. `app.py` becomes the top-level page router; target ≤ 250 lines.

**Verification**:
- Streamlit dev mode (`streamlit run app.py`) renders identically to
  before — manual sanity check.
- `wc -l frontend/app.py` ≤ 250.

---

## Task 3 — Move city→state map server-side

**Scope**: `web/components/atoms.jsx:6-50`,
`backend/routers/` (new endpoint or extend existing geo route),
`backend/data/`.

**Steps**:

1. Move the hardcoded city→state dict from `atoms.jsx` into
   `backend/data/cities.py` (or a JSON file under `backend/data/`).
2. Expose via `GET /geo/cities` → list of `{city, state}`.
3. In `atoms.jsx`, fetch on first mount and cache in component state /
   a `useQuery` hook.

**Verification**:
- React build doesn't include the dict (search the bundle output).
- Page loads still work offline-after-first-visit (cache) — verify in
  Network tab.

---

## Task 4 — Remove PRAGMA f-string

**Scope**: `backend/services/db.py:41-46` (or wherever the migration
moves after P2 Task 2 / Alembic).

**Steps**:

1. After P2 Task 2 lands, this code is gone. If P2 Task 2 hasn't landed
   yet, replace `f"PRAGMA table_info({table})"` with an allowlist guard:
   ```python
   ALLOWED_TABLES = {"alert_subscriptions", "webpush_subscriptions", "alerts"}
   if table not in ALLOWED_TABLES:
       raise ValueError(f"unknown table: {table}")
   ```

**Verification**:
- `grep -n "f.*PRAGMA" backend/` returns nothing.

---

## Task 5 — Slim React view components

**Scope**: `web/components/views/*.jsx`.

**Steps**:

1. For each `View*.jsx` > 250 lines, extract:
   - form state → `useViewXyzForm()` custom hook in
     `web/components/views/hooks/`.
   - API calls → `useViewXyzData()` query hook.
   - Sub-sections that only one parent renders → still inline; sections
     used in 2+ places → into `web/components/`.
2. Target ≤ 250 lines per view component.

**Verification**:
- `wc -l web/components/views/*.jsx` all ≤ 250.
- Manual click-through of each view in the dev server confirms no
  regressions.

---

## Task 6 — Streamline numeric scaling smell

**Scope**: `backend/ml/acoustic_model.py:76`.

**Steps**:

1. The line `peak_bin = int(np.argmax(...) * 15 / (len(...) + 1))` has
   off-by-one risk depending on intent. Read the surrounding function,
   determine whether the intent is "scale argmax index to [0, 15]" and
   replace with explicit `np.clip(int(... * 15 / max(len(...), 1)), 0, 15)`
   or refactor to a documented helper.

**Verification**:
- Add a unit test that pins the expected output for known inputs at the
  array-size boundaries.
- `pytest tests/test_acoustic_model_scaling.py` green.

---

## Task 7 — Doc pass

**Scope**: top-level `README.md`, `docs/`.

**Steps**:

1. Update `README.md` with the new auth model (P0 Task 3), how to set up
   `.env` from `.env.example`, how to run Alembic, where the audit docs
   live.
2. Add a `docs/architecture.md` describing the
   router → service → ML/data flow, the i18n middleware path, and where
   PII is encrypted.
3. Cross-link from `README.md` to `docs/audit/P0..P3` so future
   contributors find the work-in-progress remediation.

**Verification**:
- A fresh contributor can go from `git clone` to running tests using
  only `README.md`. (Try it on a clean machine or in a Docker `python:3.11-slim`.)

---

## Out of scope

- Strategic decisions: Postgres migration, Streamlit→React consolidation,
  ML backend reduction beyond what Task 1 covers. Raise these with the
  user separately.

## Done criteria

- All seven verification blocks pass.
- `requirements.txt` is fully pinned and split.
- No view component or page module > 250 lines.
- Fresh-clone install + boot is reproducible from `README.md` alone.
