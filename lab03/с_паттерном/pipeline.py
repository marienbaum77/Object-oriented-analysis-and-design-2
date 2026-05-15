# pipeline.py
from __future__ import annotations

import abc
from typing import Optional

from moex_chain_trader.context import TradeContext


class BaseHandler(abc.ABC):
    """Abstract handler in the Chain of Responsibility pattern."""
    
    def __init__(self):
        self._next_handler: Optional[BaseHandler] = None
    
    def set_next(self, handler: BaseHandler) -> BaseHandler:
        """Set the next handler in the chain and return it for chaining."""
        self._next_handler = handler
        return handler
    
    def handle(self, ctx: TradeContext) -> None:
        """Process the context or pass to next handler."""
        if not ctx.stop_chain:
            self.process(ctx)
        
        # Pass to next handler if chain shouldn't stop
        if self._next_handler and not ctx.stop_chain:
            self._next_handler.handle(ctx)
    
    @abc.abstractmethod
    def process(self, ctx: TradeContext) -> None:
        """Concrete processing logic to be implemented by subclasses."""
        pass
