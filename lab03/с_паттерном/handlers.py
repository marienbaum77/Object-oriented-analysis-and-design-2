from __future__ import annotations

import os
import sys
import time
from typing import Any, List, Optional

from moex_chain_trader.context import TradeContext
from moex_chain_trader.pipeline import BaseHandler

VIRTUAL_COMMISSION_RATE = 0.0001  # 0.01%


def _parse_float_cell(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (value != value):  # NaN
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


class PriceSanitizer(BaseHandler):
    """Validates MOEX marketdata, maps LAST prices, applies commission to trade unit economics."""

    def handle(self, ctx: TradeContext) -> None:
        name = self.__class__.__name__
        ctx.prices_gross.clear()
        ctx.unit_price_gross = None
        ctx.unit_price_buy = None
        ctx.unit_price_sell = None

        if ctx.raw_market_rows and ctx.market_columns:
            try:
                idx_sec = ctx.market_columns.index("SECID")
                idx_last = ctx.market_columns.index("LAST")
            except ValueError:
                ctx.stop_chain = True
                ctx.stop_reason = "Marketdata columns must include SECID and LAST"
                ctx.log(name, ctx.stop_reason)
                return

            for row in ctx.raw_market_rows:
                if not isinstance(row, list) or len(row) <= max(idx_sec, idx_last):
                    continue
                secid = str(row[idx_sec]).strip().upper()
                last = _parse_float_cell(row[idx_last])
                ctx.prices_gross[secid] = last

            ctx.log(name, f"Sanitized {len(ctx.prices_gross)} TQBR rows")
        else:
            if ctx.event in {"tick", "poll"}:
                ctx.log(name, "No marketdata rows attached")
                return

        if ctx.event in {"buy", "sell"} and ctx.ticker:
            t = ctx.ticker.upper()
            gross = ctx.prices_gross.get(t)
            if gross is None or gross <= 0:
                ctx.stop_chain = True
                ctx.stop_reason = f"Missing or invalid LAST price for {t}"
                ctx.log(name, ctx.stop_reason)
                return
            ctx.unit_price_gross = gross
            ctx.unit_price_buy = gross * (1.0 + VIRTUAL_COMMISSION_RATE)
            ctx.unit_price_sell = gross * (1.0 - VIRTUAL_COMMISSION_RATE)
            ctx.log(
                name,
                f"{t} gross={gross:.4f} buy_unit={ctx.unit_price_buy:.6f} sell_unit={ctx.unit_price_sell:.6f}",
            )


class AuthValidator(BaseHandler):
    """Buy: sufficient RUB. Sell: sufficient inventory."""

    def handle(self, ctx: TradeContext) -> None:
        name = self.__class__.__name__
        if ctx.event == "buy":
            if not ctx.ticker or ctx.quantity <= 0:
                ctx.stop_chain = True
                ctx.stop_reason = "Invalid buy command"
                ctx.log(name, ctx.stop_reason)
                return
            if ctx.unit_price_buy is None:
                ctx.stop_chain = True
                ctx.stop_reason = "Buy blocked: unit buy price unavailable (await market tick)"
                ctx.log(name, ctx.stop_reason)
                return
            need = ctx.quantity * ctx.unit_price_buy
            bal, _ = ctx.portfolio.snapshot()
            if bal + 1e-9 < need:
                ctx.stop_chain = True
                ctx.stop_reason = f"Insufficient virtual balance: need {need:,.2f} RUB, have {bal:,.2f} RUB"
                ctx.log(name, ctx.stop_reason)
                return
            ctx.log(name, f"Buy authorized - required {need:,.2f} RUB")
        elif ctx.event == "sell":
            if not ctx.ticker or ctx.quantity <= 0:
                ctx.stop_chain = True
                ctx.stop_reason = "Invalid sell command"
                ctx.log(name, ctx.stop_reason)
                return
            if ctx.unit_price_sell is None:
                ctx.stop_chain = True
                ctx.stop_reason = "Sell blocked: unit sell price unavailable (await market tick)"
                ctx.log(name, ctx.stop_reason)
                return
            have = ctx.portfolio.get_holding_qty(ctx.ticker.upper())
            if have < ctx.quantity:
                ctx.stop_chain = True
                ctx.stop_reason = f"Insufficient shares: need {ctx.quantity}, have {have}"
                ctx.log(name, ctx.stop_reason)
                return
            ctx.log(name, "Sell authorized - inventory OK")
        elif ctx.event in {"tick", "poll"}:
            return
        else:
            ctx.log(name, "Skipped (unsupported event)")


class RiskManager(BaseHandler):
    """Concentration risk: post-buy ticker market value must not exceed 50% of total portfolio."""

    def handle(self, ctx: TradeContext) -> None:
        name = self.__class__.__name__
        if ctx.event != "buy" or ctx.stop_chain:
            return
        if ctx.ticker is None or ctx.unit_price_gross is None or ctx.unit_price_buy is None:
            ctx.stop_chain = True
            ctx.stop_reason = "Risk check failed: incomplete trade economics"
            ctx.log(name, ctx.stop_reason)
            return

        ticker = ctx.ticker.upper()
        bal, snap = ctx.portfolio.snapshot()
        qty_new = ctx.quantity
        price = ctx.unit_price_gross
        total_buy_cost = qty_new * ctx.unit_price_buy

        post_cash = bal - total_buy_cost
        if post_cash < -1e-6:
            ctx.stop_chain = True
            ctx.stop_reason = "RiskManager: negative post-trade cash (should not happen after Auth)"
            ctx.log(name, ctx.stop_reason)
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
            ctx.log(name, "Portfolio value ~0 - skip concentration ratio")
            return

        ticker_mv = mv_for(ticker)
        weight = ticker_mv / post_total
        if weight > 0.5 + 1e-9:
            ctx.stop_chain = True
            ctx.stop_reason = (
                f"Concentration limit: {ticker} would be {weight*100:.2f}% of portfolio (>50%)"
            )
            ctx.log(name, ctx.stop_reason)
            return
        ctx.log(name, f"Concentration OK - {ticker} weight after buy ~ {weight*100:.2f}%")


class ProfitLossCalculator(BaseHandler):
    """Unrealized P&L per holding from latest gross prices."""

    def handle(self, ctx: TradeContext) -> None:
        name = self.__class__.__name__
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
        ctx.log(name, f"Marked {len(ctx.unrealized_by_ticker)} open position(s)")


class TerminalRenderer(BaseHandler):
    """Clears the console and draws the dashboard."""

    def handle(self, ctx: TradeContext) -> None:
        name = self.__class__.__name__
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
        lines.append(row("MoexChainTrader - Paper Trading (MOEX TQBR)"))
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
        for hname, msg in ctx.status_messages[-8:]:
            chunk = f"{hname}: {msg}"
            if len(chunk) > W - 4:
                chunk = chunk[: W - 7] + "..."
            lines.append(row(chunk))

        lines.append(sep("="))
        lines.append(row("Commands: buy TICKER QTY | sell TICKER QTY | list | quit"))
        lines.append(sep("="))

        text = "\n".join(lines) + "\n"
        enc = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.buffer.write(text.encode(enc, errors="replace"))
        sys.stdout.flush()
        ctx.log(name, "Dashboard rendered")
