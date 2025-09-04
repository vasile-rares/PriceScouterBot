import json
import os
import time
from typing import Any, Dict, Optional


CACHE_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(CACHE_DIR, "cache.json")


def _now_ts() -> float:
    return time.time()


def _ensure_cache_dir():
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except Exception:
        pass


def _load_raw() -> Dict[str, Any]:
    try:
        if not os.path.exists(CACHE_FILE):
            return {}
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def load_cache() -> Dict[str, list]:
    """Load items per site. Backward compatible.

    New schema: { "items": {site: [..]}, "query_index": {site: {normalized_query: url}} }
    Old schema (backward): { site: [..] }
    """
    raw = _load_raw()
    if "items" in raw and isinstance(raw["items"], dict):
        items = raw["items"]
        return {k: (v if isinstance(v, list) else []) for k, v in items.items()}
    # old shape
    return {k: (v if isinstance(v, list) else []) for k, v in raw.items()}


def save_cache(data: Dict[str, list]) -> None:
    """Save items while preserving query_index if present."""
    _ensure_cache_dir()
    raw = _load_raw()
    raw["items"] = data
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def upsert(site: str, entry: Dict[str, Any]) -> None:
    """Insert or update an entry for a site based on URL or title."""
    cache = load_cache()
    items = cache.get(site, [])
    key_url = (entry.get("url") or "").strip()
    key_title = (entry.get("title") or "").strip().lower()

    updated = False
    for it in items:
        if (it.get("url") or "").strip() == key_url or (it.get("title") or "").strip().lower() == key_title:
            it.update({k: v for k, v in entry.items() if v is not None})
            it["saved_at"] = _now_ts()
            updated = True
            break

    if not updated:
        new_item = {k: v for k, v in entry.items() if v is not None}
        new_item["saved_at"] = _now_ts()
        items.append(new_item)

    cache[site] = items
    save_cache(cache)


def find_best(site: str, query: str, *, scorer) -> Optional[Dict[str, Any]]:
    """Return best cached match for site using provided scorer(title, query)->score.

    Requires a scorer function to avoid coupling with scraping module.
    """
    cache = load_cache()
    items = cache.get(site, [])
    best = None
    best_score = 0.0
    q = (query or "").strip()
    for it in items:
        title = it.get("title") or ""
        score = float(scorer(title, q))
        if score > best_score:
            best = it
            best_score = score
    # Consider a strong match threshold to return immediately
    if best and best_score >= 90:
        return best
    return None


def _norm_query(s: str) -> str:
    return " ".join((s or "").lower().split())


def upsert_for_query(site: str, query: str, entry: Dict[str, Any]) -> None:
    """Upsert item and map exact normalized query -> entry URL for this site."""
    upsert(site, entry)
    raw = _load_raw()
    qidx = raw.get("query_index") or {}
    site_map = qidx.get(site) or {}
    url = (entry.get("url") or "").strip()
    if url:
        site_map[_norm_query(query)] = url
        qidx[site] = site_map
        raw["query_index"] = qidx
        try:
            _ensure_cache_dir()
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def _find_by_url(site: str, url: str) -> Optional[Dict[str, Any]]:
    url = (url or "").strip()
    items = load_cache().get(site, [])
    for it in items:
        if (it.get("url") or "").strip() == url:
            return it
    return None


def get_for_query(site: str, query: str) -> Optional[Dict[str, Any]]:
    """Return cached item for exact normalized query if available."""
    raw = _load_raw()
    qidx = raw.get("query_index") or {}
    site_map = qidx.get(site) or {}
    url = site_map.get(_norm_query(query))
    if not url:
        return None
    return _find_by_url(site, url)
