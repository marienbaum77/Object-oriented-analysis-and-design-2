# pipeline.py - новый вариант
class Pipeline:
    """Facade for Chain of Responsibility."""
    
    def __init__(self, first_handler: Optional[BaseHandler] = None):
        self._first_handler = first_handler
    
    @staticmethod
    def create_chain(handlers: list[BaseHandler]) -> Pipeline:
        """Create a chain from a list of handlers."""
        if not handlers:
            return Pipeline()
        
        first = handlers[0]
        current = first
        
        for handler in handlers[1:]:
            current.set_next(handler)
            current = handler
        
        return Pipeline(first)
    
    def run(self, ctx: TradeContext, *, reset_stop: bool = True, clear_messages: bool = True) -> None:
        """Run the chain."""
        if reset_stop:
            ctx.stop_chain = False
            ctx.stop_reason = None
        if clear_messages:
            ctx.status_messages.clear()
        ctx.last_handler = None
        
        if self._first_handler:
            self._first_handler.handle(ctx)
