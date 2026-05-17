"""One-shot codemod: convert web/lib/bundles.json from flat {key: text}
to structured {key: {text, context, role}}, then mirror to backend.
Idempotent.
Run: python scripts/i18n/migrate_bundles.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web/lib/bundles.json"
BACKEND_DIR = ROOT / "backend/services/i18n/bundles"


def to_structured(value):
    if isinstance(value, dict) and "text" in value:
        return value
    return {"text": value, "context": "", "role": ""}


def main() -> None:
    data = json.loads(WEB.read_text(encoding="utf-8"))
    out = {}
    for lang, entries in data.items():
        out[lang] = {k: to_structured(v) for k, v in entries.items()}

    WEB.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"migrated {WEB.relative_to(ROOT)}")

    BACKEND_DIR.mkdir(parents=True, exist_ok=True)
    for lang, entries in out.items():
        path = BACKEND_DIR / f"{lang}.json"
        path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
