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
