"""Audio-hash response cache for the acoustic pipeline.

The full pipeline (resample + YAMNet/PANNs + maybe two API round-trips) is
expensive and deterministic for a fixed input; users retry the same upload
often enough that an LRU keyed on sha256(audio_bytes, crop_type) saves real
money and latency. Bounded so it can't grow without limit on a long-running
process.
"""

import hashlib
from typing import Optional

from cachetools import LRUCache

_RESPONSE_CACHE_MAX = 64
_RESPONSE_CACHE: "LRUCache[str, dict]" = LRUCache(maxsize=_RESPONSE_CACHE_MAX)


def _cache_key(audio_bytes: bytes, crop_type: str) -> str:
    h = hashlib.sha256()
    h.update(audio_bytes)
    h.update(b"|")
    h.update((crop_type or "").encode("utf-8"))
    return h.hexdigest()


def _cache_get(key: str) -> Optional[dict]:
    # cachetools.LRUCache already promotes on __getitem__.
    if key in _RESPONSE_CACHE:
        return _RESPONSE_CACHE[key]
    return None


def _cache_put(key: str, value: dict) -> None:
    _RESPONSE_CACHE[key] = value
