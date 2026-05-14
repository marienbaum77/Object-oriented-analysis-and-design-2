from __future__ import annotations

import abc
from typing import Iterable, List

from moex_chain_trader.context import TradeContext


class BaseHandler(abc.ABC):
    """Abstract handler in the Chain of Responsibility (flat pipeline)."""

    @abc.abstractmethod
    def handle(self, ctx: TradeContext) -> None:
        """Process ctx; may set ctx.stop_chain to break the pipeline."""


class Pipeline:
    """Runs TradeContext through an ordered flat list of handlers."""

    def __init__(self, handlers: Iterable[BaseHandler]):
        self._handlers: List[BaseHandler] = list(handlers)

    @property
    def handlers(self) -> List[BaseHandler]:
        return list(self._handlers)

    def run(self, ctx: TradeContext, *, reset_stop: bool = True, clear_messages: bool = True) -> None:
        if reset_stop:
            ctx.stop_chain = False
            ctx.stop_reason = None
        if clear_messages:
            ctx.status_messages.clear()
        ctx.last_handler = None
        for handler in self._handlers:
            if ctx.stop_chain:
                break
            handler.handle(ctx)
