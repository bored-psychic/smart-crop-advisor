"""Validate web/lib/bundles.json — completeness + placeholder integrity.

Exit code 0 = clean, 1 = violations. Designed for pre-commit + CI.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_BUNDLES = ROOT / "web/lib/bundles.json"
NON_EN_LANGS = ["hi", "te", "ta", "kn", "mr", "bn", "gu", "pa", "ml"]
PLACEHOLDER_RE = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}|%[sd]")


def _placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER_RE.findall(text or ""))


def lint(bundles: dict, non_en_langs: list[str] = NON_EN_LANGS) -> list[str]:
    errors: list[str] = []
    en = bundles.get("en", {})
    if not en:
        return ["bundles.json missing 'en' root"]
    for lang in non_en_langs:
        lb = bundles.get(lang, {})
        for key, en_entry in en.items():
            if key not in lb or not (lb[key].get("text") or "").strip():
                errors.append(f"[{lang}] missing key: {key!r}")
                continue
            txt = lb[key]["text"]
            if txt.strip() == en_entry["text"].strip():
                errors.append(f"[{lang}] {key!r}: translation equals en")
            en_ph = _placeholders(en_entry["text"])
            tr_ph = _placeholders(txt)
            if en_ph != tr_ph:
                errors.append(
                    f"[{lang}] {key!r}: placeholder mismatch en={sorted(en_ph)} tr={sorted(tr_ph)}"
                )
        for key in lb:
            if key not in en:
                errors.append(f"[{lang}] extra key not in en: {key!r}")
    return errors


def main() -> int:
    bundles = json.loads(WEB_BUNDLES.read_text())
    errors = lint(bundles)
    if not errors:
        print(f"OK: bundles.json clean across {len(NON_EN_LANGS)} non-en languages")
        return 0
    print(f"FAIL: {len(errors)} violation(s)", file=sys.stderr)
    for e in errors:
        print("  " + e, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
