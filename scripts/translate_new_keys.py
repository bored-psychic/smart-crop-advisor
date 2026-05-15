#!/usr/bin/env python3
"""
translate_new_keys.py — Translate new i18n keys and merge into bundles.json

Usage:
    python scripts/translate_new_keys.py --keys '{"Crop Advisor":"Crop Advisor","Leaf Doctor":"Leaf Doctor"}'
    python scripts/translate_new_keys.py --file new_keys.json

The script:
1. Reads new keys (English text) from --keys JSON or --file
2. Calls Claude claude-haiku-4-5 to translate each into 8 Indian languages
3. Merges results into web/lib/bundles.json and core/bundles.json
4. Prints a diff of what was added
"""

import argparse
import json
import sys
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).parent.parent
WEB_BUNDLES = REPO_ROOT / "web" / "lib" / "bundles.json"
CORE_BUNDLES = REPO_ROOT / "core" / "bundles.json"

TARGET_LANGS = {
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
}

SYSTEM_PROMPT = """You are an expert translator specialising in Indian regional languages used in agricultural contexts.
You translate short UI strings (button labels, section headers, status messages) from English into Indian languages.

Rules:
- Keep translations concise — they must fit in UI labels
- Preserve any emoji at the start of a string (e.g. 🌱, 🌿)
- Preserve ellipsis (…) at the end of loading messages
- Use commonly understood agricultural vocabulary
- For terms like "Crop Advisor", use natural equivalents that a farmer would recognise
- Respond ONLY with a valid JSON object, no explanation"""


def translate_keys(keys: dict[str, str]) -> dict[str, dict[str, str]]:
    """
    Translate a dict of {key: english_text} into all 8 target languages.
    Returns {key: {lang: translation, ...}, ...}
    """
    client = anthropic.Anthropic()

    lang_list = "\n".join(
        f'  "{code}": "{name}"' for code, name in TARGET_LANGS.items()
    )

    keys_json = json.dumps(keys, ensure_ascii=False, indent=2)

    user_prompt = f"""Translate each English UI string below into these 8 Indian languages:
{{{lang_list}
}}

Input strings (key → English text):
{keys_json}

Return a JSON object structured as:
{{
  "<key>": {{
    "hi": "<Hindi translation>",
    "te": "<Telugu translation>",
    "ta": "<Tamil translation>",
    "kn": "<Kannada translation>",
    "bn": "<Bengali translation>",
    "mr": "<Marathi translation>",
    "gu": "<Gujarati translation>",
    "pa": "<Punjabi translation>"
  }},
  ...
}}

Include ALL keys from the input. Respond with ONLY the JSON object."""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # remove first and last fence lines
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    return json.loads(text)


def load_bundles(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_bundles(path: Path, bundles: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundles, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_translations(
    bundles: dict,
    new_keys: dict[str, str],
    translations: dict[str, dict[str, str]],
) -> list[tuple[str, str, str]]:
    """
    Merge translations into bundles dict in-place.
    Returns list of (key, lang, value) tuples for all added entries.
    """
    added = []
    for key, en_text in new_keys.items():
        # English
        if key not in bundles.get("en", {}):
            bundles.setdefault("en", {})[key] = en_text
            added.append((key, "en", en_text))

        # Other languages
        lang_translations = translations.get(key, {})
        for lang_code in TARGET_LANGS:
            translated = lang_translations.get(lang_code)
            if translated and key not in bundles.get(lang_code, {}):
                bundles.setdefault(lang_code, {})[key] = translated
                added.append((key, lang_code, translated))

    return added


def main():
    parser = argparse.ArgumentParser(description="Translate new i18n keys and merge into bundles.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--keys",
        type=str,
        help='JSON string of {key: english_text} pairs, e.g. \'{"Crop Advisor":"Crop Advisor"}\'',
    )
    group.add_argument(
        "--file",
        type=str,
        help="Path to JSON file containing {key: english_text} pairs",
    )
    args = parser.parse_args()

    # Load new keys
    if args.keys:
        new_keys = json.loads(args.keys)
    else:
        with open(args.file, "r", encoding="utf-8") as f:
            new_keys = json.load(f)

    if not new_keys:
        print("No keys to translate.", file=sys.stderr)
        sys.exit(1)

    print(f"Translating {len(new_keys)} key(s): {', '.join(new_keys.keys())}")

    # Translate
    print("Calling Claude claude-haiku-4-5 for translations...")
    translations = translate_keys(new_keys)
    print(f"Received translations for {len(translations)} key(s).")

    # Load and update web/lib/bundles.json
    if not WEB_BUNDLES.exists():
        print(f"ERROR: {WEB_BUNDLES} not found", file=sys.stderr)
        sys.exit(1)

    bundles = load_bundles(WEB_BUNDLES)
    added = merge_translations(bundles, new_keys, translations)
    save_bundles(WEB_BUNDLES, bundles)
    print(f"\nUpdated: {WEB_BUNDLES}")

    # Mirror to core/bundles.json if it exists
    if CORE_BUNDLES.exists():
        core_bundles = load_bundles(CORE_BUNDLES)
        merge_translations(core_bundles, new_keys, translations)
        save_bundles(CORE_BUNDLES, core_bundles)
        print(f"Mirrored: {CORE_BUNDLES}")

    # Print diff
    if added:
        print(f"\n--- Added {len(added)} entries ---")
        current_key = None
        for key, lang, val in added:
            if key != current_key:
                print(f'\n  "{key}":')
                current_key = key
            print(f'    "{lang}": "{val}"')
    else:
        print("\nNo new entries added (all keys already present).")


if __name__ == "__main__":
    main()
