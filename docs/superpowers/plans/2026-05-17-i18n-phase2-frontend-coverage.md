# i18n Phase 2 — Frontend Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Wrap every user-visible English string in the React frontend with `t(...)` so every screen is fully translatable, with a repeatable extractor that proves zero unwrapped strings remain.

**Architecture:** Build a Python AST-free regex extractor (`scripts/i18n/extract_strings.py`) that scans `web/components/**/*.jsx` for likely user-facing string literals — JSX text children, `aria-label`/`title`/`placeholder` attribute values, and string args to known UI helpers — while ignoring style strings, className, prop names, console/log messages, and existing `t(...)` calls. Use it to produce a baseline report, then wrap files one by one. Every new English literal is also added (with English text and `context: ""`, `role: ""`) to `web/lib/bundles.json` so Phase 3's LLM pass can translate them. Re-run extractor at the end → must report zero.

**Tech Stack:** Python 3 stdlib (regex), React via CDN, existing `window.makeT(lang)` shim.

**Reference spec:** `docs/superpowers/specs/2026-05-17-multilingual-app-design.md`, section "Phase 2".

**Phase 1 prerequisites (already done):** langs codegen, structured bundle schema, server-side catalog, LocaleMiddleware, preferred_lang DB columns, frontend `Accept-Language` + localStorage persistence.

**Out of scope:** Translation quality / non-English bundle content (Phase 3). Backend response localization (Phase 4). LLM prompt directives (Phase 5). SMS/push templates (Phase 6). BCP-47 wiring for speech APIs — no `speechSynthesis` or `SpeechRecognition` callsites exist in the codebase; spec item 4 is deferred to whenever those land.

---

## File Structure

**Created:**
- `scripts/i18n/extract_strings.py` — scan jsx for unwrapped user-facing strings
- `scripts/i18n/add_keys_to_bundle.py` — helper: idempotently add missing English keys to `bundles.json` (and mirror to `backend/services/i18n/bundles/en.json`)
- `tests/test_extract_strings.py` — extractor unit tests
- `docs/i18n/phase2-baseline.md` — extractor baseline report (informational; committed)

**Modified (wrap pass):**
- `web/components/atoms.jsx`
- `web/components/app.jsx`
- `web/components/Login.jsx`
- `web/components/garden.jsx`
- `web/components/views/ViewCrop.jsx`
- `web/components/views/ViewDisease.jsx`
- `web/components/views/ViewMarket.jsx`
- `web/components/views/ViewIrrigation.jsx`
- `web/components/views/ViewAcoustic.jsx`
- `web/components/views/ViewField.jsx`
- `web/lib/bundles.json` (new English keys added)
- `backend/services/i18n/bundles/en.json` (mirror)

---

## Conventions for the wrap pass

Each wrapping subagent MUST follow these rules:

1. **What to wrap:** JSX text children that render to the DOM; `placeholder`, `title`, `aria-label`, `alt` attribute string values; string args to `alert()`, `confirm()`, `toast(...)` style helpers if they show user-facing text. Wrap as `{t('Exact English Text')}` for children, `placeholder={t('...')}`for attributes.
2. **What NOT to wrap:** `className`, `style`, prop names, CSS values, `data-*`, `id`, URL/path strings, fetch/API endpoint strings, `console.log/warn/error`, error messages thrown to dev tools only, unit symbols (`%`, `°C`, `kg/ha`) when alone, numbers, single punctuation, or any string already inside `t(...)`.
3. **Use the existing `t` prop.** Every view already receives `t` (verified). If a sub-component doesn't, thread it through props. Do NOT call `window.makeT` inside components.
4. **Preserve exact English text** — that becomes the bundle key.
5. **Mixed strings (text + variable):** use template-style — `{t('You have')} {n} {t('items')}` is wrong; instead extract the whole pattern as one key with a placeholder, e.g., `{t('You have {n} items').replace('{n}', n)}`. Keep it simple: don't introduce ICU — just `.replace('{name}', value)` chained. Document the placeholder names in the bundle by leaving English with `{name}` literally.
6. **Collect new keys.** While wrapping, append each new English string to a per-file list. After wrapping each file, run `python scripts/i18n/add_keys_to_bundle.py <key1> <key2> ...` to add them idempotently.
7. **Do not rename existing wrapped keys** — even if the casing looks off — to avoid orphaning translations.

---

## Task 1: Build the extractor

**Files:**
- Create: `scripts/i18n/extract_strings.py`
- Create: `tests/test_extract_strings.py`

- [ ] **Step 1: Write the failing test**

`tests/test_extract_strings.py`:
```python
"""Tests for the JSX unwrapped-string extractor."""
from pathlib import Path
from scripts.i18n.extract_strings import find_unwrapped_strings


def _run(src: str):
    return [m.text for m in find_unwrapped_strings(src, filename="x.jsx")]


def test_finds_jsx_text_children():
    src = """function X(){ return <div>Hello world</div>; }"""
    assert "Hello world" in _run(src)


def test_ignores_t_wrapped():
    src = """function X({t}){ return <div>{t('Hello')}</div>; }"""
    assert _run(src) == []


def test_finds_placeholder_attribute():
    src = """function X(){ return <input placeholder="Type here" />; }"""
    assert "Type here" in _run(src)


def test_finds_aria_label_and_title():
    src = """function X(){ return <button aria-label="Close" title="Dismiss" />; }"""
    out = _run(src)
    assert "Close" in out and "Dismiss" in out


def test_ignores_classname_and_style_and_id():
    src = """function X(){ return <div className="btn primary" id="root" style={{color:'red'}} />; }"""
    assert _run(src) == []


def test_ignores_pure_numbers_and_punctuation():
    src = """function X(){ return <span>42</span>; }"""
    assert _run(src) == []


def test_ignores_existing_t_call_attribute():
    src = """function X({t}){ return <input placeholder={t('Type')} />; }"""
    assert _run(src) == []


def test_ignores_url_like_strings():
    src = """const u = "/api/crop"; const v = "https://x.com";"""
    assert _run(src) == []


def test_ignores_console_calls():
    src = """function X(){ console.log("debug only"); }"""
    assert _run(src) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extract_strings.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement the extractor**

`scripts/i18n/extract_strings.py`:
```python
"""Extract likely user-facing English strings from JSX that are NOT wrapped in t(...).

Heuristic regex-based scanner — not a full JS parser, but tuned for the codebase
patterns (JSX text children, common UI attributes, string literals as args to
common helpers). False positives are acceptable; false negatives are the failure mode.

Run:
    python scripts/i18n/extract_strings.py                 # scan web/components/**/*.jsx
    python scripts/i18n/extract_strings.py path/to/file.jsx
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOB = "web/components/**/*.jsx"

# Attributes worth translating
UI_ATTRS = ("placeholder", "title", "aria-label", "alt")

# Attributes never worth translating
IGNORE_ATTRS = (
    "className", "class", "style", "id", "key", "ref", "src", "href", "type",
    "name", "value", "role", "data-", "htmlFor", "for", "rel", "target",
    "onClick", "onChange", "onSubmit", "onBlur", "onFocus", "onInput",
)


@dataclass
class Match:
    file: str
    line: int
    text: str
    kind: str  # "jsx-text" | "attr"


def _is_meaningful(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if len(s) < 2:
        return False
    # pure numeric / punctuation
    if re.fullmatch(r"[\d\s\W]+", s):
        return False
    # looks like url / path / endpoint / mime / css value
    if s.startswith(("/", "http://", "https://", "data:", "mailto:")):
        return False
    if re.fullmatch(r"[a-z][a-z0-9_-]*", s):  # single CSS-like token
        return False
    if re.fullmatch(r"#[0-9a-fA-F]{3,8}", s):  # hex color
        return False
    # must contain at least one ASCII letter
    if not re.search(r"[A-Za-z]", s):
        return False
    return True


def _strip_comments_and_strings_in_console(src: str) -> str:
    """Blank out console.* / alert calls so we don't pick up their literal args."""
    return re.sub(
        r"\bconsole\.(log|warn|error|debug|info)\s*\([^)]*\)",
        lambda m: " " * len(m.group(0)),
        src,
    )


def find_unwrapped_strings(src: str, filename: str = "<src>") -> List[Match]:
    out: List[Match] = []
    cleaned = _strip_comments_and_strings_in_console(src)

    # 1. JSX text children: >TEXT< where TEXT contains letters and no { or <.
    #    Skip if the enclosing context is obviously not JSX (best-effort).
    for m in re.finditer(r">([^<>{}\n]+?)<", cleaned):
        text = m.group(1).strip()
        if not _is_meaningful(text):
            continue
        line = cleaned[: m.start()].count("\n") + 1
        out.append(Match(file=filename, line=line, text=text, kind="jsx-text"))

    # 2. Attribute string literals: attr="value"
    attr_re = re.compile(r'(\b[\w:-]+)\s*=\s*"([^"\n]+)"')
    for m in attr_re.finditer(cleaned):
        attr, val = m.group(1), m.group(2)
        if attr in IGNORE_ATTRS or any(attr.startswith(p) for p in IGNORE_ATTRS):
            continue
        if attr not in UI_ATTRS:
            continue
        if not _is_meaningful(val):
            continue
        line = cleaned[: m.start()].count("\n") + 1
        out.append(Match(file=filename, line=line, text=val, kind="attr"))

    # 3. Attribute with t(...) — already wrapped, drop any text-match overlap
    # (handled implicitly: t-wrapped values are inside {...}, not "...")

    return out


def scan_files(paths: Iterable[Path]) -> List[Match]:
    matches: List[Match] = []
    for p in paths:
        src = p.read_text(encoding="utf-8")
        rel = str(p.relative_to(ROOT)) if p.is_absolute() else str(p)
        matches.extend(find_unwrapped_strings(src, filename=rel))
    return matches


def main(argv: List[str]) -> int:
    if len(argv) > 1:
        paths = [Path(a) for a in argv[1:]]
    else:
        paths = sorted(ROOT.glob(DEFAULT_GLOB))
    matches = scan_files(paths)

    by_file: dict[str, list[Match]] = {}
    for m in matches:
        by_file.setdefault(m.file, []).append(m)

    for f in sorted(by_file):
        print(f"\n{f}  ({len(by_file[f])} unwrapped)")
        for m in by_file[f]:
            print(f"  L{m.line:>4} [{m.kind:>9}]  {m.text}")

    print(f"\nTOTAL: {len(matches)} unwrapped strings across {len(by_file)} files")
    return 0 if not matches else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_extract_strings.py -v`
Expected: 9 PASSED.

- [ ] **Step 5: Generate the baseline report**

Run:
```bash
python scripts/i18n/extract_strings.py > docs/i18n/phase2-baseline.md 2>&1 || true
mkdir -p docs/i18n
python scripts/i18n/extract_strings.py > docs/i18n/phase2-baseline.md 2>&1 || true
head -5 docs/i18n/phase2-baseline.md
wc -l docs/i18n/phase2-baseline.md
```
Expected: baseline file exists, lists unwrapped strings per file. Exit code may be non-zero (intentional).

- [ ] **Step 6: Commit**

```bash
git add scripts/i18n/extract_strings.py tests/test_extract_strings.py docs/i18n/phase2-baseline.md
git commit -m "feat(i18n): JSX unwrapped-string extractor + baseline report"
```

---

## Task 2: Bundle-key helper script

**Files:**
- Create: `scripts/i18n/add_keys_to_bundle.py`

- [ ] **Step 1: Implement the helper**

`scripts/i18n/add_keys_to_bundle.py`:
```python
"""Idempotently add English keys to web/lib/bundles.json (en bundle) and
mirror them to backend/services/i18n/bundles/en.json. Other languages
remain untouched — Phase 3 LLM pass fills them later.

Usage:
    python scripts/i18n/add_keys_to_bundle.py "First key" "Second key" ...
    cat keys.txt | python scripts/i18n/add_keys_to_bundle.py -
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web/lib/bundles.json"
BACKEND_EN = ROOT / "backend/services/i18n/bundles/en.json"


def _entry(text: str) -> dict:
    return {"text": text, "context": "", "role": ""}


def main(argv: list[str]) -> int:
    keys = argv[1:]
    if keys == ["-"]:
        keys = [line.rstrip("\n") for line in sys.stdin if line.strip()]
    if not keys:
        print("no keys", file=sys.stderr)
        return 1

    data = json.loads(WEB.read_text(encoding="utf-8"))
    en = data.setdefault("en", {})
    added = 0
    for k in keys:
        if k in en:
            continue
        en[k] = _entry(k)
        added += 1
    WEB.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    BACKEND_EN.write_text(
        json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"added {added} new keys (en); {len(en)} total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 2: Smoke test idempotence**

Run:
```bash
python scripts/i18n/add_keys_to_bundle.py "Crop Recommender"  # already present → 0 added
python scripts/i18n/add_keys_to_bundle.py "__phase2_test_key__"  # 1 added
python scripts/i18n/add_keys_to_bundle.py "__phase2_test_key__"  # 0 added
python -c "import json; d=json.load(open('web/lib/bundles.json')); assert '__phase2_test_key__' in d['en']; del d['en']['__phase2_test_key__']; json.dump(d, open('web/lib/bundles.json','w'), ensure_ascii=False, indent=2); open('web/lib/bundles.json','a').write('\n')"
# also restore backend mirror
python -c "import json; d=json.load(open('web/lib/bundles.json')); json.dump(d['en'], open('backend/services/i18n/bundles/en.json','w'), ensure_ascii=False, indent=2); open('backend/services/i18n/bundles/en.json','a').write('\n')"
```
Expected: prints "added 0", "added 1", "added 0".

- [ ] **Step 3: Commit**

```bash
git add scripts/i18n/add_keys_to_bundle.py
git commit -m "feat(i18n): helper script to idempotently add English keys to bundles"
```

---

## Tasks 3–10: Wrap pass (one file per task)

**Pattern for every wrap task:**

1. Read the file end to end.
2. Run extractor on JUST this file: `python scripts/i18n/extract_strings.py <path>` and capture the list.
3. For each match, edit the file:
   - JSX text child `>Foo<` → `>{t('Foo')}<`
   - Attribute `placeholder="Foo"` → `placeholder={t('Foo')}`
   - Mixed text+expression: keep the English literal as one key with `{name}` placeholders; use `.replace()` chain.
4. If a sub-component inside the same file lacks `t` in its props, thread it through from the parent (which always has it).
5. Collect the list of new English strings; pipe through `add_keys_to_bundle.py`.
6. Re-run extractor on the file → MUST report zero. If non-zero, fix and re-run.
7. Commit with a focused message.

Each wrap task ends with:
```bash
python scripts/i18n/extract_strings.py <the file>  # MUST print "TOTAL: 0 unwrapped"
git add <the file> web/lib/bundles.json backend/services/i18n/bundles/en.json
git commit -m "feat(i18n): wrap user-facing strings in <component>"
```

---

### Task 3: Wrap `web/components/atoms.jsx`

**Why first:** shared primitives used by every view; threading patterns established here propagate.

**Files:** Modify `web/components/atoms.jsx`, `web/lib/bundles.json`, `backend/services/i18n/bundles/en.json`.

Follow the wrap pattern above. After commit:
```bash
python scripts/i18n/extract_strings.py web/components/atoms.jsx
# Expected: TOTAL: 0 unwrapped
```

---

### Task 4: Wrap `web/components/app.jsx` + `web/components/Login.jsx` + `web/components/garden.jsx`

**Why grouped:** all are small shells (app=174L, Login=130L, garden=8L). Single commit OK if changes are independent and tests don't bind them together.

Follow the wrap pattern per file. After all three:
```bash
python scripts/i18n/extract_strings.py \
  web/components/app.jsx web/components/Login.jsx web/components/garden.jsx
# Expected: TOTAL: 0 unwrapped
```
Single commit message: `feat(i18n): wrap app shell + Login + garden strings`.

---

### Task 5: Wrap `web/components/views/ViewCrop.jsx`

Wrap pattern. Commit message: `feat(i18n): wrap ViewCrop strings`.

---

### Task 6: Wrap `web/components/views/ViewDisease.jsx`

Wrap pattern. Commit message: `feat(i18n): wrap ViewDisease strings`.

---

### Task 7: Wrap `web/components/views/ViewMarket.jsx`

Wrap pattern. Commit message: `feat(i18n): wrap ViewMarket strings`.

---

### Task 8: Wrap `web/components/views/ViewIrrigation.jsx`

Wrap pattern. Commit message: `feat(i18n): wrap ViewIrrigation strings`.

---

### Task 9: Wrap `web/components/views/ViewAcoustic.jsx`

Wrap pattern. This is the larger view (458L) — be especially careful threading `t` into nested sub-components defined in the same file. Commit message: `feat(i18n): wrap ViewAcoustic strings`.

---

### Task 10: Wrap `web/components/views/ViewField.jsx`

Wrap pattern. Largest view (481L). Commit message: `feat(i18n): wrap ViewField strings`.

---

## Task 11: Final integration verification

**Files:** none modified — verification only.

- [ ] **Step 1: Run extractor across the whole frontend**

Run:
```bash
python scripts/i18n/extract_strings.py
echo "exit=$?"
```
Expected: `TOTAL: 0 unwrapped strings across 0 files` and `exit=0`.

If non-zero, identify the offending files and either dispatch a fix or, if the strings are false positives (e.g., placeholder tokens used as keys), extend the extractor's ignore list — but prefer wrapping over loosening.

- [ ] **Step 2: Run full test suite**

Run: `pytest -x`
Expected: no new failures vs. Phase 1 baseline (the pre-existing `test_soil_analysis_endpoint` fixture error remains acceptable).

- [ ] **Step 3: Smoke-test the web app**

Run:
```bash
cd web && python3 -m http.server 5173 >/tmp/web.log 2>&1 &
sleep 1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/lib/bundles.json
curl -s http://localhost:5173/lib/bundles.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('en keys:', len(d['en']))"
kill %1 2>/dev/null
```
Expected: 200 response; "en keys" count is meaningfully larger than the Phase 1 baseline (≥ 363).

- [ ] **Step 4: Update baseline report**

Run:
```bash
python scripts/i18n/extract_strings.py > docs/i18n/phase2-baseline.md 2>&1 || true
git add docs/i18n/phase2-baseline.md
git diff --cached --stat
git commit -m "docs(i18n): refresh phase 2 baseline (now zero)" || echo "nothing to commit"
```

---

## Phase exit criteria

- Extractor reports zero unwrapped strings across `web/components/**/*.jsx`.
- All Phase 1 tests still pass; extractor tests pass.
- `web/lib/bundles.json` and `backend/services/i18n/bundles/en.json` contain every newly wrapped key.
- Web app boots, language picker still works; switching language now visibly translates more of the UI for languages that already have Hindi/Telugu/etc. entries from Phase 1 — un-translated keys fall back to English text via `t()` semantics.
- `git log --oneline` shows ~10 focused commits, one per task (small files may be grouped).

When all criteria met, this phase is shippable. Phase 3 (LLM translation pipeline) takes the now-complete English key list and fills the other 9 languages.
