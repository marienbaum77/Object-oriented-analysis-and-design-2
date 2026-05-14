from __future__ import annotations

import os
import re
import sys
import threading
from typing import Any, List, Optional, Tuple

from moex_chain_trader.context import (
    Portfolio,
    TradeContext,
    default_state_path,
    load_portfolio_from_disk,
    save_portfolio_to_disk,
)
from moex_chain_trader.handlers import (
    AuthValidator,
    PriceSanitizer,
    ProfitLossCalculator,
    RiskManager,
    TerminalRenderer,
)
from moex_chain_trader.moex_client import fetch_tqbr_marketdata, fetch_tqbr_securities
from moex_chain_trader.pipeline import Pipeline

# Full CoR pipeline for market ticks. Order: sanitize prices -> auth -> risk -> MTM -> UI.
FULL_PIPELINE_HANDLERS = [
    PriceSanitizer(),
    AuthValidator(),
    RiskManager(),
    ProfitLossCalculator(),
    TerminalRenderer(),
]

VALIDATION_HANDLERS = [
    PriceSanitizer(),
    AuthValidator(),
    RiskManager(),
]

PRESENTATION_HANDLERS = [
    ProfitLossCalculator(),
    TerminalRenderer(),
]


def _write_stdout(text: str) -> None:
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.buffer.write(text.encode(enc, errors="replace"))


class MoexChainTraderApp:
    """Main controller: background MOEX polling + interactive order entry."""

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
        self._full_pipeline = Pipeline(FULL_PIPELINE_HANDLERS)
        self._validation_pipeline = Pipeline(VALIDATION_HANDLERS)
        self._presentation_pipeline = Pipeline(PRESENTATION_HANDLERS)
        self._lock = threading.RLock()
        self._shutdown = threading.Event()
        self._last_columns: Optional[List[str]] = None
        self._last_rows: Optional[List[List[Any]]] = None
        self._last_network_error: Optional[str] = None

    def _persist(self) -> None:
        try:
            save_portfolio_to_disk(self.portfolio, self._state_path)
        except OSError:
            pass

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

    def _maybe_settle(self, ctx: TradeContext) -> None:
        if ctx.stop_chain:
            return
        if ctx.event == "buy" and ctx.ticker and ctx.unit_price_buy is not None and ctx.quantity > 0:
            total = ctx.quantity * ctx.unit_price_buy
            self.portfolio.apply_buy(ctx.ticker.upper(), ctx.quantity, total)
            ctx.log("Settlement", f"BUY {ctx.quantity} {ctx.ticker.upper()} for {total:,.2f} RUB (incl. commission)")
            self._persist()
        elif ctx.event == "sell" and ctx.ticker and ctx.unit_price_sell is not None and ctx.quantity > 0:
            proceeds = ctx.quantity * ctx.unit_price_sell
            self.portfolio.apply_sell(ctx.ticker.upper(), ctx.quantity, proceeds)
            ctx.log("Settlement", f"SELL {ctx.quantity} {ctx.ticker.upper()} proceeds {proceeds:,.2f} RUB (net of commission)")
            self._persist()

    def _run_tick(self) -> None:
        self._refresh_market_cache()
        ctx = self._build_context("tick")
        self._full_pipeline.run(ctx)

    def _run_user_order(self, event: str, ticker: str, qty: int) -> None:
        self._refresh_market_cache()
        ctx = self._build_context(event, ticker=ticker, quantity=qty)
        self._validation_pipeline.run(ctx)
        self._maybe_settle(ctx)
        self._presentation_pipeline.run(ctx, reset_stop=False, clear_messages=False)

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

    def _parse_command(self, line: str) -> Optional[Tuple[str, Optional[str], int]]:
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
                cmd = self._parse_command(line)
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
            self._persist()
            poll_thread.join(timeout=self._poll_interval_s + 2.0)


def run() -> None:
    interval = float(os.environ.get("MOEXCHAIN_POLL_SECONDS", "30"))
    MoexChainTraderApp(poll_interval_s=interval).run()


if __name__ == "__main__":
    run()
