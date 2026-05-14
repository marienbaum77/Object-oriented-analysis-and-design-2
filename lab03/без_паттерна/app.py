from __future__ import annotations

import os
import re
import sys
import threading
import time
from typing import Any, List, Optional, Tuple

from context import (
    Portfolio,
    TradeContext,
    default_state_path,
    load_portfolio_from_disk,
    save_portfolio_to_disk,
)
from moex_client import fetch_tqbr_marketdata, fetch_tqbr_securities

VIRTUAL_COMMISSION_RATE = 0.0001  # 0.01%


def _write_stdout(text: str) -> None:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write(text.encode(enc, errors="replace"))


def _parse_command(line: str) -> Optional[Tuple[str, Optional[str], int]]:
    s = line.strip()
    if not s:
        return None
    low = s.lower()
    if low in {"q", "quit", "exit"}:
        return ("quit", None, 0)
    if low in {"list", "ls", "securities", "tickers"}:
        return ("list", None, 0)
    m = re.match(r"^(buy|sell)\s+([A-Za-z][A-Za-z0-9-]*)\s+(\d+)\s*$", low)
    if not m:
        return ("unknown", None, 0)
    side, sym, q = m.group(1), m.group(2).upper(), int(m.group(3))
    if q <= 0:
        return ("unknown", None, 0)
    return (side, sym, q)


def _parse_float_cell(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value):
            return None
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s or s.upper() in {"NULL", "N/A", "NA", "-"}:
            return None
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return None
    return None


def _sanitize_market_data(ctx: TradeContext) -> None:
    ctx.prices_gross.clear()
    ctx.unit_price_gross = None
    ctx.unit_price_buy = None
    ctx.unit_price_sell = None

    if not ctx.raw_market_rows or not ctx.market_columns:
        if ctx.event in {"tick", "poll"}:
            ctx.log("Sanitize", "No marketdata rows attached")
        return

    try:
        idx_sec = ctx.market_columns.index("SECID")
        idx_last = ctx.market_columns.index("LAST")
    except ValueError:
        ctx.stop_chain = True
        ctx.stop_reason = "Marketdata columns must include SECID and LAST"
        ctx.log("Sanitize", ctx.stop_reason)
        return

    for row in ctx.raw_market_rows:
        if not isinstance(row, list) or len(row) <= max(idx_sec, idx_last):
            continue
        secid = str(row[idx_sec]).strip().upper()
        last = _parse_float_cell(row[idx_last])
        ctx.prices_gross[secid] = last

    ctx.log("Sanitize", f"Sanitized {len(ctx.prices_gross)} TQBR rows")


def _validate_order(ctx: TradeContext) -> None:
    if ctx.event == "buy":
        if not ctx.ticker or ctx.quantity <= 0:
            ctx.stop_chain = True
            ctx.stop_reason = "Invalid buy command"
            ctx.log("Auth", ctx.stop_reason)
            return
        if ctx.unit_price_buy is None:
            ctx.stop_chain = True
            ctx.stop_reason = "Buy blocked: unit buy price unavailable (await market tick)"
            ctx.log("Auth", ctx.stop_reason)
            return
        need = ctx.quantity * ctx.unit_price_buy
        bal, _ = ctx.portfolio.snapshot()
        if bal + 1e-9 < need:
            ctx.stop_chain = True
            ctx.stop_reason = f"Insufficient virtual balance: need {need:,.2f} RUB, have {bal:,.2f} RUB"
            ctx.log("Auth", ctx.stop_reason)
            return
        ctx.log("Auth", f"Buy authorized - required {need:,.2f} RUB")
    elif ctx.event == "sell":
        if not ctx.ticker or ctx.quantity <= 0:
            ctx.stop_chain = True
            ctx.stop_reason = "Invalid sell command"
            ctx.log("Auth", ctx.stop_reason)
            return
        if ctx.unit_price_sell is None:
            ctx.stop_chain = True
            ctx.stop_reason = "Sell blocked: unit sell price unavailable (await market tick)"
            ctx.log("Auth", ctx.stop_reason)
            return
        have = ctx.portfolio.get_holding_qty(ctx.ticker.upper())
        if have < ctx.quantity:
            ctx.stop_chain = True
            ctx.stop_reason = f"Insufficient shares: need {ctx.quantity}, have {have}"
            ctx.log("Auth", ctx.stop_reason)
            return
        ctx.log("Auth", "Sell authorized - inventory OK")


def _check_risk(ctx: TradeContext) -> None:
    if ctx.event != "buy" or ctx.stop_chain:
        return
    if ctx.ticker is None or ctx.unit_price_gross is None or ctx.unit_price_buy is None:
        ctx.stop_chain = True
        ctx.stop_reason = "Risk check failed: incomplete trade economics"
        ctx.log("Risk", ctx.stop_reason)
        return

    ticker = ctx.ticker.upper()
    bal, snap = ctx.portfolio.snapshot()
    qty_new = ctx.quantity
    total_buy_cost = qty_new * ctx.unit_price_buy

    post_cash = bal - total_buy_cost
    if post_cash < -1e-6:
        ctx.stop_chain = True
        ctx.stop_reason = "RiskManager: negative post-trade cash (should not happen after Auth)"
        ctx.log("Risk", ctx.stop_reason)
        return

    projected_qty: dict[str, int] = {t: q for t, (q, _) in snap.items()}
    projected_qty[ticker] = projected_qty.get(ticker, 0) + qty_new

    def mv_for(sec: str) -> float:
        p = ctx.prices_gross.get(sec)
        if p is None or p <= 0:
            if sec in snap:
                _, avg = snap[sec]
                p = avg
        return projected_qty.get(sec, 0) * (p or 0.0)

    total_mv = sum(mv_for(s) for s in projected_qty)
    post_total = post_cash + total_mv
    if post_total <= 1e-6:
        ctx.log("Risk", "Portfolio value ~0 - skip concentration ratio")
        return

    ticker_mv = mv_for(ticker)
    weight = ticker_mv / post_total
    if weight > 0.5 + 1e-9:
        ctx.stop_chain = True
        ctx.stop_reason = (
            f"Concentration limit: {ticker} would be {weight*100:.2f}% of portfolio (>50%)"
        )
        ctx.log("Risk", ctx.stop_reason)
        return
    ctx.log("Risk", f"Concentration OK - {ticker} weight after buy ~ {weight*100:.2f}%")


def _calculate_unrealized(ctx: TradeContext) -> None:
    ctx.unrealized_by_ticker.clear()
    _, snap = ctx.portfolio.snapshot()
    for sec, (qty, avg) in snap.items():
        if qty <= 0:
            continue
        last = ctx.prices_gross.get(sec)
        if last is None or last <= 0 or avg <= 0:
            ctx.unrealized_by_ticker[sec] = (0.0, 0.0)
            continue
        urub = (last - avg) * qty
        pctp = (last / avg - 1.0) * 100.0
        ctx.unrealized_by_ticker[sec] = (urub, pctp)
    ctx.log("PL", f"Marked {len(ctx.unrealized_by_ticker)} open position(s)")


def _render_dashboard(ctx: TradeContext) -> None:
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")

    bal, snap = ctx.portfolio.snapshot()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    W = 78

    def row(inner: str) -> str:
        inner = inner[: W - 2]
        return "| " + inner.ljust(W - 2) + " |"

    def sep(ch: str = "-") -> str:
        return "+" + ch * W + "+"

    lines: List[str] = []
    lines.append(sep("="))
    lines.append(row("MoexChainTrader - Paper Trading (NO PATTERN)"))
    lines.append(sep("="))
    if ctx.network_error:
        warn = ctx.network_error
        if len(warn) > W - 14:
            warn = warn[: W - 17] + "..."
        lines.append(row(f"Network: {warn}"))
        lines.append(sep("-"))
    positions_mv = 0.0
    for sec, (qty, avg) in snap.items():
        if qty <= 0:
            continue
        last = ctx.prices_gross.get(sec)
        px = last if last is not None and last > 0 else avg
        positions_mv += qty * float(px)

    total_equity = bal + positions_mv
    lines.append(row(f"Cash (free RUB):        {bal:>20,.2f}"))
    lines.append(row(f"Positions (mark-to-market): {positions_mv:>14,.2f}"))
    lines.append(row(f"Total equity (cash+stocks): {total_equity:>14,.2f}"))
    lines.append(row(f"Time (local): {ts}"))
    lines.append(sep("="))
    lines.append(row("Holdings: Ticker | Qty | Avg buy | Last | P&L (RUB) | P&L %"))
    lines.append(sep("-"))

    if not snap:
        lines.append(row("(no open positions)"))
    else:
        for sec in sorted(snap.keys()):
            qty, avg = snap[sec]
            last = ctx.prices_gross.get(sec)
            urub, pctp = ctx.unrealized_by_ticker.get(sec, (0.0, 0.0))
            last_s = f"{last:.4f}" if last is not None and last > 0 else "N/A"
            lines.append(
                row(
                    f"{sec:<6} | {qty:>4} | {avg:>8.4f} | {last_s:>8} | {urub:>10.2f} | {pctp:>7.2f}%"
                )
            )

    lines.append(sep("="))
    lines.append(row("Pipeline status (latest event)"))
    lines.append(sep("-"))
    if ctx.stop_chain and ctx.stop_reason:
        reason = ctx.stop_reason
        if len(reason) > W - 10:
            reason = reason[: W - 13] + "..."
        lines.append(row(f"STOP: {reason}"))
    for name, msg in ctx.status_messages[-8:]:
        chunk = f"{name}: {msg}"
        if len(chunk) > W - 4:
            chunk = chunk[: W - 7] + "..."
        lines.append(row(chunk))

    lines.append(sep("="))
    lines.append(row("Commands: buy TICKER QTY | sell TICKER QTY | list | quit"))
    lines.append(sep("="))

    text = "\n".join(lines) + "\n"
    _write_stdout(text)
    ctx.log("Render", "Dashboard rendered")


def _settle_trade(ctx: TradeContext) -> None:
    if ctx.stop_chain:
        return
    if ctx.event == "buy" and ctx.ticker and ctx.unit_price_buy is not None and ctx.quantity > 0:
        total = ctx.quantity * ctx.unit_price_buy
        ctx.portfolio.apply_buy(ctx.ticker.upper(), ctx.quantity, total)
        ctx.log("Settlement", f"BUY {ctx.quantity} {ctx.ticker.upper()} for {total:,.2f} RUB (incl. commission)")
        save_portfolio_to_disk(ctx.portfolio)
    elif ctx.event == "sell" and ctx.ticker and ctx.unit_price_sell is not None and ctx.quantity > 0:
        proceeds = ctx.quantity * ctx.unit_price_sell
        ctx.portfolio.apply_sell(ctx.ticker.upper(), ctx.quantity, proceeds)
        ctx.log("Settlement", f"SELL {ctx.quantity} {ctx.ticker.upper()} proceeds {proceeds:,.2f} RUB (net of commission)")
        save_portfolio_to_disk(ctx.portfolio)


def _execute_event(ctx: TradeContext) -> None:
    _sanitize_market_data(ctx)
    if ctx.stop_chain:
        return
    if ctx.event in {"buy", "sell"}:
        _validate_order(ctx)
        if ctx.stop_chain:
            return
        _check_risk(ctx)
        if ctx.stop_chain:
            return
        _settle_trade(ctx)
    _calculate_unrealized(ctx)
    _render_dashboard(ctx)


class MoexChainTraderApp:
    """Main controller without Chain-of-Responsibility pattern."""

    def __init__(self, poll_interval_s: float = 30.0) -> None:
        self._state_path = default_state_path()
        initial = float(os.environ.get("MOEXCHAIN_INITIAL_BALANCE", "1000000"))
        loaded = load_portfolio_from_disk(self._state_path)
        if loaded is not None:
            self.portfolio = loaded
            self._loaded_from_disk = True
        else:
            self.portfolio = Portfolio(balance_rub=initial)
            self._loaded_from_disk = False

        self._poll_interval_s = poll_interval_s
        self._lock = threading.RLock()
        self._shutdown = threading.Event()
        self._last_columns: Optional[List[str]] = None
        self._last_rows: Optional[List[List[Any]]] = None
        self._last_network_error: Optional[str] = None

    def _refresh_market_cache(self) -> None:
        cols, rows, err = fetch_tqbr_marketdata()
        if err:
            self._last_network_error = err
        else:
            self._last_network_error = None
        if cols and rows is not None:
            self._last_columns = cols
            self._last_rows = rows

    def _build_context(self, event: str, ticker: Optional[str] = None, quantity: int = 0) -> TradeContext:
        return TradeContext(
            event=event,
            portfolio=self.portfolio,
            ticker=ticker,
            quantity=quantity,
            raw_market_rows=self._last_rows,
            market_columns=self._last_columns,
            network_error=self._last_network_error,
        )

    def _run_tick(self) -> None:
        self._refresh_market_cache()
        ctx = self._build_context("tick")
        _execute_event(ctx)

    def _run_user_order(self, event: str, ticker: str, qty: int) -> None:
        self._refresh_market_cache()
        ctx = self._build_context(event, ticker=ticker, quantity=qty)
        _execute_event(ctx)

    def _print_tqbr_securities(self) -> None:
        cols, rows, err = fetch_tqbr_securities()
        if err:
            _write_stdout(err + "\n")
            return
        if not cols or rows is None:
            _write_stdout("Empty securities response.\n")
            return
        try:
            i_sec = cols.index("SECID")
            i_short = cols.index("SHORTNAME") if "SHORTNAME" in cols else None
        except ValueError:
            _write_stdout("SECID column missing in ISS securities table.\n")
            return

        out_lines: List[str] = []
        out_lines.append(f"TQBR instruments ({len(rows)}). Source: MOEX ISS.")
        out_lines.append("-" * 78)
        for row in rows:
            if not isinstance(row, list) or len(row) <= i_sec:
                continue
            sec = str(row[i_sec]).strip().upper()
            if not sec:
                continue
            if i_short is not None and len(row) > i_short:
                short = str(row[i_short]).replace("\n", " ").strip()
                if len(short) > 44:
                    short = short[:41] + "..."
                out_lines.append(f"  {sec:<10}  {short}")
            else:
                out_lines.append(f"  {sec}")

        out_lines.append("-" * 78)
        _write_stdout("\n".join(out_lines) + "\n")

    def _poll_loop(self) -> None:
        while not self._shutdown.is_set():
            with self._lock:
                self._run_tick()
            if self._shutdown.wait(self._poll_interval_s):
                break

    def run(self) -> None:
        print("MoexChainTrader starting - loading TQBR marketdata...")
        if self._loaded_from_disk:
            print(f"Portfolio loaded from: {self._state_path}")
        else:
            print(f"No saved state at {self._state_path} - starting fresh (see MOEXCHAIN_INITIAL_BALANCE).")

        poll_thread = threading.Thread(target=self._poll_loop, name="MoexPoll", daemon=True)
        poll_thread.start()

        try:
            while not self._shutdown.is_set():
                try:
                    line = input("> ")
                except EOFError:
                    break
                cmd = _parse_command(line)
                if cmd is None:
                    continue
                kind, sym, qty = cmd
                if kind == "quit":
                    self._shutdown.set()
                    break
                if kind == "unknown":
                    print("Unknown command. Use: buy TICKER QTY | sell TICKER QTY | list | quit")
                    continue
                with self._lock:
                    if kind == "list":
                        self._print_tqbr_securities()
                    elif kind in {"buy", "sell"} and sym is not None:
                        self._run_user_order(kind, sym, qty)
        finally:
            self._shutdown.set()
            save_portfolio_to_disk(self.portfolio)
            poll_thread.join(timeout=self._poll_interval_s + 2.0)


def run() -> None:
    interval = float(os.environ.get("MOEXCHAIN_POLL_SECONDS", "30"))
    MoexChainTraderApp(poll_interval_s=interval).run()


if __name__ == "__main__":
    run()
