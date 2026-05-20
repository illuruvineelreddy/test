"""
Paper Trading Engine for Project Astra
Simulates real trading with virtual money, slippage, and latency
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid
import random

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order status states"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PaperTradingEngine:
    """
    Simulates live trading with virtual portfolio
    Includes realistic slippage, latency, and fill simulation
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.portfolio_value = initial_capital
        
        # Positions: symbol -> {qty, avg_price, current_price, unrealized_pnl}
        self.positions: Dict[str, Dict] = {}
        
        # Orders tracking
        self.orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []
        
        # Performance metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # Simulation parameters
        self.slippage_percent = 0.05  # 0.05% slippage
        self.latency_ms = 100  # 100ms simulated latency
        self.fill_probability = 0.95  # 95% fill rate
        
        logger.info(f"Paper Trading initialized with capital: ₹{initial_capital:,.2f}")
    
    def place_order(
        self,
        symbol: str,
        transaction_type: str,  # BUY or SELL
        quantity: int,
        order_type: str,  # MARKET or LIMIT
        price: Optional[float] = None,
        strategy: str = "MANUAL",
        stop_loss: Optional[float] = None,
        target: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place a simulated order
        
        Returns:
            Order details with order_id
        """
        order_id = f"PAPER_{uuid.uuid4().hex[:12]}"
        
        # Simulate latency
        import time
        time.sleep(self.latency_ms / 1000)
        
        # Create order
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'order_type': order_type,
            'price': price,
            'strategy': strategy,
            'stop_loss': stop_loss,
            'target': target,
            'status': OrderStatus.PENDING,
            'filled_qty': 0,
            'avg_fill_price': 0.0,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
        }
        
        self.orders[order_id] = order
        
        # Simulate market price if not provided
        if price is None:
            # Use mock price based on symbol
            base_prices = {
                'NIFTY': 22000.0,
                'BANKNIFTY': 47000.0,
                'FINNIFTY': 21000.0,
                'RELIANCE': 2900.0,
                'TCS': 4100.0,
            }
            price = base_prices.get(symbol, 1000.0)
        
        # Simulate slippage
        slippage = price * (random.uniform(-0.0005, 0.0005))
        fill_price = price + slippage
        
        # Check fill probability
        if random.random() > self.fill_probability:
            order['status'] = OrderStatus.REJECTED
            order['rejection_reason'] = 'Simulated rejection'
            logger.warning(f"Order {order_id} rejected (simulated)")
            return order
        
        # Execute order
        if transaction_type == 'BUY':
            self._execute_buy(order, fill_price)
        else:
            self._execute_sell(order, fill_price)
        
        # Update order
        order['status'] = OrderStatus.FILLED
        order['filled_qty'] = quantity
        order['avg_fill_price'] = fill_price
        order['updated_at'] = datetime.now()
        
        # Add to history
        self.order_history.append(order.copy())
        
        self.total_trades += 1
        
        logger.info(
            f"[PAPER TRADE] {transaction_type} {quantity} {symbol} @ ₹{fill_price:.2f} | "
            f"Order ID: {order_id}"
        )
        
        return order
    
    def _execute_buy(self, order: Dict, fill_price: float):
        """Execute buy order"""
        symbol = order['symbol']
        quantity = order['quantity']
        total_cost = fill_price * quantity
        
        # Check if we have enough capital
        if total_cost > self.current_capital:
            order['status'] = OrderStatus.REJECTED
            order['rejection_reason'] = 'Insufficient capital'
            logger.warning(f"Order rejected: Insufficient capital")
            return
        
        # Deduct capital
        self.current_capital -= total_cost
        
        # Update or create position
        if symbol in self.positions:
            pos = self.positions[symbol]
            old_qty = pos['qty']
            old_avg = pos['avg_price']
            
            new_qty = old_qty + quantity
            new_avg = ((old_qty * old_avg) + (quantity * fill_price)) / new_qty
            
            pos['qty'] = new_qty
            pos['avg_price'] = new_avg
            pos['current_price'] = fill_price
        else:
            self.positions[symbol] = {
                'qty': quantity,
                'avg_price': fill_price,
                'current_price': fill_price,
                'unrealized_pnl': 0.0
            }
        
        logger.debug(f"Updated position for {symbol}: {self.positions[symbol]}")
    
    def _execute_sell(self, order: Dict, fill_price: float):
        """Execute sell order"""
        symbol = order['symbol']
        quantity = order['quantity']
        
        # Check if we have the position
        if symbol not in self.positions:
            order['status'] = OrderStatus.REJECTED
            order['rejection_reason'] = 'No position to sell'
            logger.warning(f"Order rejected: No position in {symbol}")
            return
        
        pos = self.positions[symbol]
        
        if pos['qty'] < quantity:
            order['status'] = OrderStatus.REJECTED
            order['rejection_reason'] = 'Insufficient quantity'
            logger.warning(f"Order rejected: Only {pos['qty']} qty available")
            return
        
        # Calculate PnL
        pnl = (fill_price - pos['avg_price']) * quantity
        self.realized_pnl += pnl
        self.total_pnl += pnl
        
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1
        
        # Add proceeds to capital
        total_proceeds = fill_price * quantity
        self.current_capital += total_proceeds
        
        # Update position
        pos['qty'] -= quantity
        
        if pos['qty'] == 0:
            del self.positions[symbol]
        else:
            pos['current_price'] = fill_price
        
        logger.debug(f"Updated position for {symbol}: {self.positions.get(symbol, 'Closed')}")
        logger.info(f"Realized PnL: ₹{pnl:.2f}")
    
    def update_prices(self, prices: Dict[str, float]):
        """
        Update current prices for all positions
        Call this periodically with latest market prices
        """
        total_unrealized = 0.0
        
        for symbol, pos in self.positions.items():
            if symbol in prices:
                current_price = prices[symbol]
                pos['current_price'] = current_price
                
                # Calculate unrealized PnL
                pnl = (current_price - pos['avg_price']) * pos['qty']
                pos['unrealized_pnl'] = pnl
                total_unrealized += pnl
        
        self.unrealized_pnl = total_unrealized
        self.portfolio_value = self.current_capital + total_unrealized
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order['status'] in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            return False
        
        order['status'] = OrderStatus.CANCELLED
        order['updated_at'] = datetime.now()
        
        logger.info(f"Order {order_id} cancelled")
        return True
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
        return [
            {
                'symbol': symbol,
                **data
            }
            for symbol, data in self.positions.items()
        ]
    
    def get_orders(self, status: Optional[OrderStatus] = None) -> List[Dict]:
        """Get orders, optionally filtered by status"""
        if status:
            return [
                order for order in self.orders.values()
                if order['status'] == status
            ]
        return list(self.orders.values())
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get complete portfolio summary"""
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'portfolio_value': self.portfolio_value,
            'total_pnl': self.total_pnl,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / self.total_trades * 100 if self.total_trades > 0 else 0,
            'positions_count': len(self.positions),
            'timestamp': datetime.now().isoformat()
        }
    
    def reset(self):
        """Reset paper trading account"""
        self.__init__(self.initial_capital)
        logger.info("Paper trading account reset")


# Singleton instance
paper_trading_engine = PaperTradingEngine(initial_capital=100000.0)


def get_paper_trading_engine() -> PaperTradingEngine:
    """Get paper trading engine instance"""
    return paper_trading_engine
