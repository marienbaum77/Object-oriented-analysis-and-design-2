class PriceSanitizer(BaseHandler):
    """Validates MOEX marketdata, maps LAST prices, applies commission to trade unit economics."""
    
    def process(self, ctx: TradeContext) -> None:  # Было: handle
        name = self.__class__.__name__
        # ... остальной код без изменений


class AuthValidator(BaseHandler):
    """Buy: sufficient RUB. Sell: sufficient inventory."""
    
    def process(self, ctx: TradeContext) -> None:  # Было: handle
        name = self.__class__.__name__
        # ... остальной код без изменений


class RiskManager(BaseHandler):
    """Concentration risk: post-buy ticker market value must not exceed 50% of total portfolio."""
    
    def process(self, ctx: TradeContext) -> None:  # Было: handle
        name = self.__class__.__name__
        # ... остальной код без изменений


class ProfitLossCalculator(BaseHandler):
    """Unrealized P&L per holding from latest gross prices."""
    
    def process(self, ctx: TradeContext) -> None:  # Было: handle
        name = self.__class__.__name__
        # ... остальной код без изменений


class TerminalRenderer(BaseHandler):
    """Clears the console and draws the dashboard."""
    
    def process(self, ctx: TradeContext) -> None:  # Было: handle
        name = self.__class__.__name__
        # ... остальной код без изменений
