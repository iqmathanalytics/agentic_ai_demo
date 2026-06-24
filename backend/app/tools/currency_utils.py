"""Currency conversion helpers for displaying stock reports in Malaysian Ringgit."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

TARGET_CURRENCY = "MYR"

# Conservative fallbacks used only if live FX cannot be reached.
_FALLBACK_TO_MYR = {
    "MYR": 1.0,
    "RM": 1.0,
    "USD": 4.70,
    "EUR": 5.05,
    "GBP": 5.95,
    "SGD": 3.48,
    "INR": 0.056,
    "JPY": 0.030,
    "CNY": 0.65,
    "HKD": 0.60,
    "AUD": 3.10,
    "CAD": 3.45,
}

_FX_CACHE: dict[str, tuple[float, float]] = {}
_FX_TTL_SECONDS = 60 * 60 * 6


def normalize_currency(currency: Any, exchange: str = "") -> str:
    if currency:
        cur = str(currency).strip().upper()
        if cur in {"RM", "MYR"}:
            return "MYR"
        if len(cur) == 3:
            return cur

    exchange_upper = (exchange or "").upper()
    if exchange_upper in {"NSE", "BSE"}:
        return "INR"
    if exchange_upper in {"MYX", "BURSA", "KLSE"}:
        return "MYR"
    if exchange_upper in {"SGX"}:
        return "SGD"
    if exchange_upper in {"LSE"}:
        return "GBP"
    if exchange_upper in {"TSE", "TYO"}:
        return "JPY"
    if exchange_upper in {"HKEX", "HKG"}:
        return "HKD"
    return "USD"


def get_fx_rate_to_myr(source_currency: str) -> float:
    source = normalize_currency(source_currency)
    if source == TARGET_CURRENCY:
        return 1.0

    now = time.time()
    cached = _FX_CACHE.get(source)
    if cached and now - cached[1] < _FX_TTL_SECONDS:
        return cached[0]

    # Allow ops to override if a provider is unavailable or a fixed rate is needed.
    env_key = f"FX_{source}_TO_MYR"
    if os.getenv(env_key):
        try:
            rate = float(os.environ[env_key])
            _FX_CACHE[source] = (rate, now)
            return rate
        except ValueError:
            logger.warning("Invalid %s value: %s", env_key, os.environ[env_key])

    try:
        import httpx

        response = httpx.get(
            "https://api.frankfurter.app/latest",
            params={"from": source, "to": TARGET_CURRENCY},
            timeout=8,
            follow_redirects=True,
        )
        data = response.json()
        rate = float((data.get("rates") or {}).get(TARGET_CURRENCY))
        if rate > 0:
            _FX_CACHE[source] = (rate, now)
            return rate
    except Exception as exc:
        logger.warning("Live FX lookup failed for %s->MYR: %s", source, exc)

    fallback = _FALLBACK_TO_MYR.get(source, 1.0)
    _FX_CACHE[source] = (fallback, now)
    return fallback


def convert_to_myr(value: Any, source_currency: str) -> Any:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return value
    rate = get_fx_rate_to_myr(source_currency)
    return round(float(value) * rate, 4)
