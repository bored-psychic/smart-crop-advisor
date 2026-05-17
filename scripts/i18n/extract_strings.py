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
