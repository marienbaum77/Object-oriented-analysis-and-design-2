from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Holding:
    quantity: int = 0
    avg_buy_price: float = 0.0


@dataclass
class Portfolio:
    """Thread-safe virtual portfolio (RUB cash + TQBR holdings)."""

    balance_rub: float
    holdings: Dict[str, Holding] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def snapshot(self) -> Tuple[float, Dict[str, Tuple[int, float]]]:
        with self._lock:
            h = {t: (v.quantity, v.avg_buy_price) for t, v in self.holdings.items() if v.quantity > 0}
            return self.balance_rub, h

    def get_holding_qty(self, ticker: str) -> int:
        with self._lock:
            h = self.holdings.get(ticker)
            return h.quantity if h else 0

    def apply_buy(self, ticker: str, qty: int, total_cost_rub: float) -> None:
        with self._lock:
            if total_cost_rub > self.balance_rub + 1e-9:
                raise ValueError("Insufficient balance for settlement")
            self.balance_rub -= total_cost_rub
            cur = self.holdings.get(ticker) or Holding()
            new_qty = cur.quantity + qty
            if new_qty <= 0:
                return
            per_share = total_cost_rub / qty
            if cur.quantity > 0:
                cur.avg_buy_price = (cur.quantity * cur.avg_buy_price + qty * per_share) / new_qty
            else:
                cur.avg_buy_price = per_share
            cur.quantity = new_qty
            self.holdings[ticker] = cur

    def apply_sell(self, ticker: str, qty: int, proceeds_rub: float) -> None:
        with self._lock:
            cur = self.holdings.get(ticker)
            if not cur or cur.quantity < qty:
                raise ValueError("Insufficient shares for settlement")
            cur.quantity -= qty
            self.balance_rub += proceeds_rub
            if cur.quantity == 0:
                del self.holdings[ticker]

    def to_storage_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "balance_rub": self.balance_rub,
                "holdings": {
                    t: {"quantity": h.quantity, "avg_buy_price": h.avg_buy_price}
                    for t, h in self.holdings.items()
                    if h.quantity > 0
                },
            }

    @staticmethod
    def from_storage_dict(data: Dict[str, Any]) -> "Portfolio":
        bal = float(data.get("balance_rub", 0.0))
        p = Portfolio(balance_rub=bal)
        raw = data.get("holdings") or {}
        if isinstance(raw, dict):
            with p._lock:
                for t, v in raw.items():
                    if not isinstance(v, dict):
                        continue
                    q = int(v.get("quantity", 0))
                    if q <= 0:
                        continue
                    avg = float(v.get("avg_buy_price", 0.0))
                    p.holdings[str(t).upper()] = Holding(quantity=q, avg_buy_price=avg)
        return p


default_state_path = lambda: os.path.join(os.getcwd(), "moex_chain_trader_state.json")


def load_portfolio_from_disk(path: Optional[str] = None) -> Optional[Portfolio]:
    p = path or default_state_path()
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return Portfolio.from_storage_dict(data)


def save_portfolio_to_disk(portfolio: Portfolio, path: Optional[str] = None) -> None:
    p = path or default_state_path()
    tmp = f"{p}.tmp"
    payload = json.dumps(portfolio.to_storage_dict(), ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(payload)
    os.replace(tmp, p)


@dataclass
class TradeContext:
    """Mutable execution context for a single trade or market tick."""

    event: str
    portfolio: Portfolio
    ticker: Optional[str] = None
    quantity: int = 0
    raw_market_rows: Optional[List[List[Any]]] = None
    market_columns: Optional[List[str]] = None
    prices_gross: Dict[str, Optional[float]] = field(default_factory=dict)
    unit_price_gross: Optional[float] = None
    unit_price_buy: Optional[float] = None
    unit_price_sell: Optional[float] = None
    unrealized_by_ticker: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    status_messages: List[Tuple[str, str]] = field(default_factory=list)
    last_stage: Optional[str] = None
    stop_chain: bool = False
    stop_reason: Optional[str] = None
    network_error: Optional[str] = None

    def log(self, stage_name: str, message: str) -> None:
        self.status_messages.append((stage_name, message))
        self.last_stage = stage_name
