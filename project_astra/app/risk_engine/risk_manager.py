"""
Risk Management Engine - Position sizing, kill switches, and risk controls
MOST IMPORTANT MODULE
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import redis
import json
from loguru import logger

from configs.settings import settings


class RiskLevel(Enum):
    """Risk levels for trades"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Result of risk assessment for a trade"""
    approved: bool
    position_size: int
    risk_level: RiskLevel
    reason: str
    max_loss: float
    expected_return: float
    risk_reward_ratio: float


class RiskEngine:
    """
    Central risk management system
    Enforces position limits, loss limits, and kill switches
    """
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        # Capital tracking
        self.initial_capital = settings.INITIAL_CAPITAL
        self.current_capital = self.initial_capital
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.consecutive_losses = 0
        self.last_reset_date = datetime.now().date()
        
        # Position tracking
        self.active_positions: Dict[str, dict] = {}
        self.total_exposure = 0.0
        
        # Kill switch state
        self.kill_switch_active = False
        self.kill_switch_reason: Optional[str] = None
        
        logger.info(f"RiskEngine initialized with capital: ₹{self.initial_capital:,.2f}")
    
    def _reset_daily_counters(self):
        """Reset daily counters if it's a new trading day"""
        today = datetime.now().date()
        if today > self.last_reset_date:
            logger.info("Resetting daily risk counters")
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.consecutive_losses = 0
            self.last_reset_date = today
            self.kill_switch_active = False
            self.kill_switch_reason = None
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        strategy: str
    ) -> int:
        """
        Calculate position size based on risk per trade
        
        Formula: PositionSize = AccountRisk / (EntryPrice - StopLoss)
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            strategy: Strategy name
            
        Returns:
            Quantity to trade
        """
        # Amount willing to risk on this trade (1% of capital)
        account_risk = self.current_capital * (settings.RISK_PER_TRADE_PCT / 100)
        
        # Per-unit risk
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit <= 0:
            logger.warning(f"Invalid stop loss for {symbol}: entry={entry_price}, sl={stop_loss}")
            return 0
        
        # Calculate quantity
        quantity = account_risk / risk_per_unit
        
        # Round down to nearest lot size (simplified - assuming 1 lot = 1 unit)
        quantity = int(quantity)
        
        # Apply minimum quantity check
        if quantity < settings.MIN_LIQUIDITY_QTY:
            logger.warning(f"Position size too small for {symbol}: {quantity}")
            return 0
        
        # Check total exposure limit
        proposed_exposure = quantity * entry_price
        max_exposure = self.current_capital * settings.MAX_LEVERAGE
        
        if self.total_exposure + proposed_exposure > max_exposure:
            logger.warning(f"Exposure limit reached for {symbol}")
            return 0
        
        logger.info(
            f"Position size calculated for {symbol}: {quantity} units, "
            f"risk: ₹{account_risk:.2f}, exposure: ₹{proposed_exposure:,.2f}"
        )
        
        return quantity
    
    def assess_trade(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        target_price: float,
        strategy: str,
        ml_confidence: float = 0.5
    ) -> RiskAssessment:
        """
        Comprehensive risk assessment for a potential trade
        
        Returns RiskAssessment with approval decision and position size
        """
        # Reset daily counters if needed
        self._reset_daily_counters()
        
        # Check kill switch first
        if self.kill_switch_active:
            return RiskAssessment(
                approved=False,
                position_size=0,
                risk_level=RiskLevel.CRITICAL,
                reason=f"Kill switch active: {self.kill_switch_reason}",
                max_loss=0,
                expected_return=0,
                risk_reward_ratio=0
            )
        
        # Check daily loss limit
        daily_loss_limit = self.initial_capital * (settings.DAILY_LOSS_LIMIT_PCT / 100)
        if self.daily_pnl < -daily_loss_limit:
            logger.error(f"Daily loss limit exceeded: ₹{self.daily_pnl:.2f}")
            self.activate_kill_switch("Daily loss limit exceeded")
            return RiskAssessment(
                approved=False,
                position_size=0,
                risk_level=RiskLevel.CRITICAL,
                reason="Daily loss limit exceeded",
                max_loss=0,
                expected_return=0,
                risk_reward_ratio=0
            )
        
        # Check consecutive losses
        if self.consecutive_losses >= settings.MAX_CONSECUTIVE_LOSSES:
            logger.warning(f"Max consecutive losses reached: {self.consecutive_losses}")
            return RiskAssessment(
                approved=False,
                position_size=0,
                risk_level=RiskLevel.HIGH,
                reason=f"Max consecutive losses ({settings.MAX_CONSECUTIVE_LOSSES}) reached",
                max_loss=0,
                expected_return=0,
                risk_reward_ratio=0
            )
        
        # Check maximum positions
        if len(self.active_positions) >= settings.MAX_POSITIONS:
            logger.warning(f"Maximum positions reached: {len(self.active_positions)}")
            return RiskAssessment(
                approved=False,
                position_size=0,
                risk_level=RiskLevel.MEDIUM,
                reason=f"Maximum positions ({settings.MAX_POSITIONS}) reached",
                max_loss=0,
                expected_return=0,
                risk_reward_ratio=0
            )
        
        # Calculate position size
        quantity = self.calculate_position_size(symbol, entry_price, stop_loss, strategy)
        
        if quantity <= 0:
            return RiskAssessment(
                approved=False,
                position_size=0,
                risk_level=RiskLevel.MEDIUM,
                reason="Invalid position size",
                max_loss=0,
                expected_return=0,
                risk_reward_ratio=0
            )
        
        # Calculate risk metrics
        max_loss = quantity * abs(entry_price - stop_loss)
        potential_profit = quantity * abs(target_price - entry_price)
        
        if max_loss <= 0:
            risk_reward_ratio = 0
        else:
            risk_reward_ratio = potential_profit / max_loss
        
        # Determine risk level based on various factors
        risk_level = self._determine_risk_level(
            quantity=quantity,
            entry_price=entry_price,
            ml_confidence=ml_confidence,
            risk_reward_ratio=risk_reward_ratio
        )
        
        # ML confidence filter
        if ml_confidence < settings.ML_CONFIDENCE_THRESHOLD:
            logger.info(f"ML confidence too low for {symbol}: {ml_confidence}")
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return RiskAssessment(
                    approved=False,
                    position_size=0,
                    risk_level=risk_level,
                    reason=f"ML confidence below threshold: {ml_confidence}",
                    max_loss=max_loss,
                    expected_return=potential_profit,
                    risk_reward_ratio=risk_reward_ratio
                )
        
        # Approve trade
        return RiskAssessment(
            approved=True,
            position_size=quantity,
            risk_level=risk_level,
            reason="Trade approved",
            max_loss=max_loss,
            expected_return=potential_profit,
            risk_reward_ratio=risk_reward_ratio
        )
    
    def _determine_risk_level(
        self,
        quantity: int,
        entry_price: float,
        ml_confidence: float,
        risk_reward_ratio: float
    ) -> RiskLevel:
        """Determine overall risk level for a trade"""
        exposure = quantity * entry_price
        exposure_pct = (exposure / self.current_capital) * 100
        
        # Critical: Very high exposure or very poor risk/reward
        if exposure_pct > 50 or risk_reward_ratio < 0.5:
            return RiskLevel.CRITICAL
        
        # High: High exposure or low ML confidence
        if exposure_pct > 30 or ml_confidence < 0.4 or risk_reward_ratio < 1.0:
            return RiskLevel.HIGH
        
        # Medium: Moderate exposure
        if exposure_pct > 15 or ml_confidence < 0.6:
            return RiskLevel.MEDIUM
        
        # Low: Good risk profile
        return RiskLevel.LOW
    
    def activate_kill_switch(self, reason: str):
        """Activate the kill switch to stop all trading"""
        self.kill_switch_active = True
        self.kill_switch_reason = reason
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
        # Publish alert
        try:
            self.redis_client.publish(
                "alerts:killswitch",
                json.dumps({
                    'timestamp': datetime.utcnow().isoformat(),
                    'reason': reason,
                    'action': 'ALL_TRADING_STOPPED'
                })
            )
        except Exception as e:
            logger.error(f"Error publishing kill switch alert: {e}")
    
    def deactivate_kill_switch(self):
        """Deactivate the kill switch (requires manual intervention)"""
        logger.warning("Kill switch manually deactivated")
        self.kill_switch_active = False
        self.kill_switch_reason = None
    
    def record_trade_entry(self, trade_id: str, trade_data: dict):
        """Record a new active trade"""
        self.active_positions[trade_id] = {
            **trade_data,
            'entry_time': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        # Update exposure
        qty = trade_data.get('quantity', 0)
        price = trade_data.get('entry_price', 0)
        self.total_exposure += qty * price
        
        self.daily_trades += 1
        
        logger.info(f"Trade recorded: {trade_id}, Total exposure: ₹{self.total_exposure:,.2f}")
    
    def record_trade_exit(self, trade_id: str, exit_price: float, pnl: float):
        """Record a trade exit and update PnL"""
        if trade_id not in self.active_positions:
            logger.warning(f"Trade {trade_id} not found in active positions")
            return
        
        trade = self.active_positions[trade_id]
        
        # Update exposure
        qty = trade.get('quantity', 0)
        entry_price = trade.get('entry_price', 0)
        self.total_exposure -= qty * entry_price
        
        # Update PnL
        self.daily_pnl += pnl
        self.current_capital += pnl
        
        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Remove from active positions
        trade['exit_time'] = datetime.utcnow().isoformat()
        trade['exit_price'] = exit_price
        trade['pnl'] = pnl
        trade['status'] = 'closed'
        
        del self.active_positions[trade_id]
        
        logger.info(
            f"Trade closed: {trade_id}, PnL: ₹{pnl:,.2f}, "
            f"Daily PnL: ₹{self.daily_pnl:,.2f}, Capital: ₹{self.current_capital:,.2f}"
        )
    
    def get_risk_summary(self) -> dict:
        """Get current risk summary"""
        self._reset_daily_counters()
        
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'total_pnl': self.current_capital - self.initial_capital,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': (self.daily_pnl / self.initial_capital) * 100,
            'daily_trades': self.daily_trades,
            'consecutive_losses': self.consecutive_losses,
            'active_positions': len(self.active_positions),
            'total_exposure': self.total_exposure,
            'exposure_pct': (self.total_exposure / self.current_capital) * 100,
            'kill_switch_active': self.kill_switch_active,
            'kill_switch_reason': self.kill_switch_reason,
            'max_positions': settings.MAX_POSITIONS,
            'daily_loss_limit': self.initial_capital * (settings.DAILY_LOSS_LIMIT_PCT / 100),
            'remaining_daily_loss': self.daily_pnl + (self.initial_capital * (settings.DAILY_LOSS_LIMIT_PCT / 100))
        }
    
    def check_health(self) -> bool:
        """Check if risk engine is healthy and trading can continue"""
        if self.kill_switch_active:
            return False
        
        if self.daily_pnl < -(self.initial_capital * (settings.DAILY_LOSS_LIMIT_PCT / 100)):
            return False
        
        if self.consecutive_losses >= settings.MAX_CONSECUTIVE_LOSSES:
            return False
        
        return True


# Singleton instance
risk_engine = RiskEngine()
