"""Claude-API translation pipeline for web/lib/bundles.json + backend bundles.

Run:
    python scripts/i18n/translate_bundles.py --force-all       # retranslate all
    python scripts/i18n/translate_bundles.py                   # fill missing only
    python scripts/i18n/translate_bundles.py --langs hi,te     # subset
    python scripts/i18n/translate_bundles.py --dry-run         # print, don't write

Requires ANTHROPIC_API_KEY in env (loaded from .env via python-dotenv).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml
from anthropic import Anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
WEB_BUNDLES = ROOT / "web/lib/bundles.json"
BACKEND_BUNDLES_DIR = ROOT / "backend/services/i18n/bundles"
GLOSSARY = Path(__file__).parent / "glossary.yaml"
LANGS_YAML = Path(__file__).parent / "langs.yaml"
REPORT = Path(__file__).parent / "translation_report.md"

MODEL = "claude-opus-4-7"
BATCH_SIZE = 30
NON_EN_LANGS_FALLBACK = ["hi", "te", "ta", "kn", "mr", "bn", "gu", "pa", "ml"]


def compute_work_list(
    bundles: dict,
    langs: list[str],
    force_all: bool,
    keys: Optional[list[str]],
) -> list[tuple[str, str]]:
    """Return [(lang, key)] pairs needing translation."""
    en = bundles["en"]
    work: list[tuple[str, str]] = []
    for lang in langs:
        lang_bundle = bundles.get(lang, {})
        for key, en_entry in en.items():
            if keys is not None and key not in keys:
                continue
            entry = lang_bundle.get(key)
            if force_all:
                work.append((lang, key))
                continue
            if entry is None:
                work.append((lang, key))
                continue
            text = (entry.get("text") or "").strip()
            if not text or text == en_entry["text"]:
                work.append((lang, key))
    return work


SYSTEM_PROMPT_TEMPLATE = """You are a professional translator for an Indian agricultural app used by farmers.

Translate UI strings into {language_name} ({lang_code}).

Rules (follow strictly):
- Natural sentence-level translation, NOT word-for-word.
- Use vocabulary an Indian farmer actually speaks (regional/colloquial > textbook).
- Keep numbers, units (kg/ha, °C, mm, %), and brand/proper names unchanged.
- Preserve markdown (**bold**, *italic*), and placeholders like %s, {{name}}, {{count}} exactly.
- Preserve trailing punctuation (. ! ? :) and casing intent of the source.
- If a term appears in the glossary below, use the pinned translation.
- Output STRICT JSON: a list of objects {{"key": "<key>", "translation": "<text>"}}. No prose, no markdown fence.

Glossary (canonical translations to reuse verbatim):
{glossary_block}
"""


def build_glossary_block(glossary: dict, lang: str) -> str:
    lines = []
    for term, trans in glossary.items():
        if lang in trans:
            lines.append(f"- {term!r} → {trans[lang]!r}")
    return "\n".join(lines) if lines else "(no pinned terms for this language)"


def translate_batch(
    client: Anthropic,
    lang: str,
    language_name: str,
    glossary: dict,
    batch: list[dict],
) -> dict[str, str]:
    """Send one batch; return {key: translation}."""
    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT_TEMPLATE.format(
                language_name=language_name,
                lang_code=lang,
                glossary_block=build_glossary_block(glossary, lang),
            ),
            "cache_control": {"type": "ephemeral"},
        }
    ]
    user_payload = json.dumps(
        [{"key": b["key"], "en_text": b["en_text"],
          "context": b.get("context", ""), "role": b.get("role", "")}
         for b in batch],
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=system,
        messages=[{"role": "user", "content": user_payload}],
    )
    text = resp.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    parsed = json.loads(text)
    return {item["key"]: item["translation"] for item in parsed}


def load_bundles() -> dict:
    return json.loads(WEB_BUNDLES.read_text())


def save_bundles(bundles: dict) -> None:
    WEB_BUNDLES.write_text(
        json.dumps(bundles, ensure_ascii=False, indent=2) + "\n"
    )
    for lang, entries in bundles.items():
        (BACKEND_BUNDLES_DIR / f"{lang}.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
        )


def write_report(changes: list[dict]) -> None:
    by_lang: dict[str, list[dict]] = {}
    for c in changes:
        by_lang.setdefault(c["lang"], []).append(c)
    lines = ["# Translation report\n"]
    for lang in sorted(by_lang):
        items = by_lang[lang]
        flagged = sum(1 for c in items if c["flagged"])
        lines.append(f"\n## {lang} — {len(items)} updated, {flagged} flagged\n")
        lines.append("| key | before | after | flag |")
        lines.append("|---|---|---|---|")
        for c in items:
            flag = "⚠️" if c["flagged"] else ""
            before = (c["before"] or "").replace("|", "\\|")
            after = c["after"].replace("|", "\\|")
            lines.append(f"| `{c['key']}` | {before} | {after} | {flag} |")
    REPORT.write_text("\n".join(lines) + "\n")


def main() -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-all", action="store_true")
    ap.add_argument("--langs", default="")
    ap.add_argument("--keys", default="")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # langs.yaml has a top-level "languages" key containing the list
    raw_cfg = yaml.safe_load(LANGS_YAML.read_text())
    langs_cfg = raw_cfg.get("languages") if isinstance(raw_cfg, dict) else raw_cfg
    all_non_en = [l["code"] for l in langs_cfg if l["code"] != "en"] \
        if isinstance(langs_cfg, list) else NON_EN_LANGS_FALLBACK
    name_by_code = {l["code"]: l.get("native_name") or l.get("english_name") or l["code"]
                    for l in langs_cfg} if isinstance(langs_cfg, list) else {}

    langs = [l for l in (args.langs.split(",") if args.langs else all_non_en) if l]
    keys = args.keys.split(",") if args.keys else None

    bundles = load_bundles()
    work = compute_work_list(bundles, langs, args.force_all, keys)
    if args.limit:
        work = work[: args.limit]
    print(f"Work: {len(work)} (lang,key) pairs across {len(langs)} langs")

    if not work:
        print("Nothing to do.")
        return 0

    glossary = yaml.safe_load(GLOSSARY.read_text())
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    en = bundles["en"]
    changes: list[dict] = []

    # group by lang, then chunk
    by_lang: dict[str, list[str]] = {}
    for lang, key in work:
        by_lang.setdefault(lang, []).append(key)

    for lang, lang_keys in by_lang.items():
        lname = name_by_code.get(lang, lang)
        print(f"\n[{lang}] {len(lang_keys)} keys")
        for i in range(0, len(lang_keys), BATCH_SIZE):
            chunk = lang_keys[i : i + BATCH_SIZE]
            batch = [
                {"key": k, "en_text": en[k]["text"],
                 "context": en[k].get("context", ""),
                 "role": en[k].get("role", "")}
                for k in chunk
            ]
            print(f"  batch {i // BATCH_SIZE + 1}: {len(batch)} keys", flush=True)
            if args.dry_run:
                print(f"  [dry-run] would translate: {[b['key'] for b in batch]}")
                continue
            try:
                results = translate_batch(client, lang, lname, glossary, batch)
            except Exception as e:
                print(f"  ERROR: {e}", file=sys.stderr)
                continue
            bundles.setdefault(lang, {})
            for k, new_text in results.items():
                before = (bundles[lang].get(k) or {}).get("text", "")
                entry = bundles[lang].get(k) or {"text": "", "context": "", "role": ""}
                entry["text"] = new_text
                bundles[lang][k] = entry
                flagged = (
                    new_text.strip() == en[k]["text"].strip()
                    or "[" in new_text and "]" in new_text
                    or "TODO" in new_text
                )
                changes.append({"lang": lang, "key": k, "before": before,
                                "after": new_text, "flagged": flagged})

    if args.dry_run:
        print("\nDRY RUN — not writing files")
    else:
        save_bundles(bundles)
        write_report(changes)
        print(f"\nWrote bundles + {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
