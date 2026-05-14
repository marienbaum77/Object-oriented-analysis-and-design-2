from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

TQBR_MARKETDATA_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/"
    "securities.json?iss.meta=off&iss.only=marketdata&marketdata.columns=SECID,LAST"
)

TQBR_SECURITIES_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/"
    "securities.json?iss.meta=off&iss.only=securities&securities.columns=SECID,SHORTNAME"
)


def fetch_tqbr_marketdata(timeout: float = 20.0) -> Tuple[Optional[List[str]], Optional[List[List[Any]]], Optional[str]]:
    req = urllib.request.Request(TQBR_MARKETDATA_URL, headers={"User-Agent": "MoexChainTrader-NoPattern/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return None, None, f"URLError: {exc.reason!s}"

    try:
        payload: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, None, f"JSONDecodeError: {exc}"

    block = payload.get("marketdata")
    if not isinstance(block, dict):
        return None, None, "Unexpected ISS payload: missing marketdata object"

    cols = block.get("columns")
    data = block.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return None, None, "Unexpected ISS payload: marketdata.columns / marketdata.data"

    return [str(c) for c in cols], data, None


def fetch_tqbr_securities(timeout: float = 30.0) -> Tuple[Optional[List[str]], Optional[List[List[Any]]], Optional[str]]:
    req = urllib.request.Request(TQBR_SECURITIES_URL, headers={"User-Agent": "MoexChainTrader-NoPattern/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        return None, None, f"URLError: {exc.reason!s}"

    try:
        payload: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, None, f"JSONDecodeError: {exc}"

    block = payload.get("securities")
    if not isinstance(block, dict):
        return None, None, "Unexpected ISS payload: missing securities object"

    cols = block.get("columns")
    data = block.get("data")
    if not isinstance(cols, list) or not isinstance(data, list):
        return None, None, "Unexpected ISS payload: securities.columns / securities.data"

    return [str(c) for c in cols], data, None
