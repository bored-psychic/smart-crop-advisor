"""Generate web/lib/langs.js and backend/services/i18n/langs.py from langs.yaml.

Run: python scripts/i18n/codegen_langs.py
"""
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("pyyaml required: pip install pyyaml")

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts/i18n/langs.yaml"
JS_OUT = ROOT / "web/lib/langs.js"
PY_OUT = ROOT / "backend/services/i18n/langs.py"

BANNER = "// GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml\n"
PY_BANNER = "# GENERATED FILE — do not edit by hand. Source: scripts/i18n/langs.yaml\n"


def main() -> None:
    data = yaml.safe_load(SRC.read_text())
    langs = data["languages"]

    js_lines = [BANNER, "window.LANGS = " + json.dumps(langs, ensure_ascii=False, indent=2) + ";\n"]
    js_lines.append("window.LANGS_BY_CODE = Object.fromEntries(window.LANGS.map(l => [l.code, l]));\n")
    js_lines.append("window.bcp47 = function(code){ return (window.LANGS_BY_CODE[code]||window.LANGS_BY_CODE['en']).bcp47; };\n")
    js_lines.append("window.isSupportedLang = function(code){ return !!window.LANGS_BY_CODE[code]; };\n")
    JS_OUT.write_text("".join(js_lines), encoding="utf-8")

    py = [PY_BANNER, "from typing import Dict\n\n"]
    py.append("LANGS: Dict[str, dict] = " + repr({l["code"]: l for l in langs}) + "\n\n")
    py.append("def is_supported(code: str) -> bool:\n    return code in LANGS\n\n")
    py.append("def bcp47(code: str) -> str:\n    return LANGS.get(code, LANGS['en'])['bcp47']\n")
    PY_OUT.write_text("".join(py), encoding="utf-8")

    print(f"wrote {JS_OUT.relative_to(ROOT)}")
    print(f"wrote {PY_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
