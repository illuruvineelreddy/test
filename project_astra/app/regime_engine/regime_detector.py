"""
Market Regime Detection Engine for Project Astra
Detects market state: Bull, Bear, Sideways, High Volatility
"""
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np
import pandas_ta as ta

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime states"""
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOL = "HIGH_VOL"
    EXPIRY_DAY = "EXPIRY_DAY"
    NEWS_EVENT = "NEWS_EVENT"


class RegimeEngine:
    """
    Detects current market regime using multiple signals
    """
    
    def __init__(self):
        self.current_regime: Optional[MarketRegime] = None
        self.regime_history: list = []
        self.last_update: Optional[datetime] = None
        
    def detect_regime(
        self,
        nifty_df: pd.DataFrame,
        banknifty_df: pd.DataFrame,
        vix: float,
        vix_change: float = 0.0,
        is_expiry: bool = False,
        is_news_event: bool = False,
        advance_decline: Optional[Dict[str, int]] = None
    ) -> MarketRegime:
        """
        Detect current market regime
        
        Args:
            nifty_df: NIFTY OHLCV data
            banknifty_df: BANKNIFTY OHLCV data
            vix: India VIX value
            vix_change: Change in VIX
            is_expiry: True if today is options expiry
            is_news_event: True if major news event today
            advance_decline: Market breadth data
            
        Returns:
            Detected market regime
        """
        try:
            # Check for special conditions first
            if is_news_event:
                regime = MarketRegime.NEWS_EVENT
                logger.info("Market regime: NEWS_EVENT")
                self._update_regime(regime)
                return regime
            
            if is_expiry:
                regime = MarketRegime.EXPIRY_DAY
                logger.info("Market regime: EXPIRY_DAY")
                self._update_regime(regime)
                return regime
            
            # Check for high volatility
            if vix > 20 or vix_change > 10:
                regime = MarketRegime.HIGH_VOL
                logger.info(f"Market regime: HIGH_VOL (VIX={vix})")
                self._update_regime(regime)
                return regime
            
            # Calculate trend indicators
            trend_score = self._calculate_trend_score(nifty_df, banknifty_df, advance_decline)
            
            # Determine regime based on trend score
            if trend_score >= 0.5:
                regime = MarketRegime.BULL
                logger.info(f"Market regime: BULL (score={trend_score})")
            elif trend_score <= -0.5:
                regime = MarketRegime.BEAR
                logger.info(f"Market regime: BEAR (score={trend_score})")
            else:
                regime = MarketRegime.SIDEWAYS
                logger.info(f"Market regime: SIDEWAYS (score={trend_score})")
            
            self._update_regime(regime)
            return regime
            
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")
            return MarketRegime.SIDEWAYS
    
    def _calculate_trend_score(
        self,
        nifty_df: pd.DataFrame,
        banknifty_df: pd.DataFrame,
        advance_decline: Optional[Dict[str, int]]
    ) -> float:
        """
        Calculate trend score from -1 (strong bear) to +1 (strong bull)
        """
        scores = []
        
        try:
            # Score 1: EMA crossover on NIFTY
            if len(nifty_df) >= 50:
                ema20 = ta.ema(nifty_df['close'], length=20).iloc[-1]
                ema50 = ta.ema(nifty_df['close'], length=50).iloc[-1]
                
                if ema20 > ema50:
                    scores.append(0.3)
                elif ema20 < ema50:
                    scores.append(-0.3)
                else:
                    scores.append(0.0)
            
            # Score 2: Price above/below SMA200
            if len(nifty_df) >= 200:
                sma200 = ta.sma(nifty_df['close'], length=200).iloc[-1]
                current_price = nifty_df['close'].iloc[-1]
                
                if current_price > sma200:
                    scores.append(0.2)
                elif current_price < sma200:
                    scores.append(-0.2)
                else:
                    scores.append(0.0)
            
            # Score 3: RSI direction
            if len(nifty_df) >= 14:
                rsi = ta.rsi(nifty_df['close'], length=14).iloc[-1]
                
                if rsi > 60:
                    scores.append(0.2)
                elif rsi < 40:
                    scores.append(-0.2)
                else:
                    scores.append(0.0)
            
            # Score 4: BANKNIFTY confirmation
            if len(banknifty_df) >= 50:
                bn_ema20 = ta.ema(banknifty_df['close'], length=20).iloc[-1]
                bn_ema50 = ta.ema(banknifty_df['close'], length=50).iloc[-1]
                
                if bn_ema20 > bn_ema50:
                    scores.append(0.15)
                elif bn_ema20 < bn_ema50:
                    scores.append(-0.15)
                else:
                    scores.append(0.0)
            
            # Score 5: Market breadth
            if advance_decline:
                advances = advance_decline.get('advance', 0)
                declines = advance_decline.get('decline', 0)
                
                if advances > declines * 1.5:
                    scores.append(0.15)
                elif declines > advances * 1.5:
                    scores.append(-0.15)
                else:
                    scores.append(0.0)
            
        except Exception as e:
            logger.error(f"Error calculating trend score: {e}")
        
        # Sum scores and normalize to [-1, 1]
        total_score = sum(scores)
        return max(min(total_score, 1.0), -1.0)
    
    def _update_regime(self, regime: MarketRegime):
        """Update current regime and history"""
        self.current_regime = regime
        self.last_update = datetime.now()
        
        self.regime_history.append({
            'regime': regime.value,
            'timestamp': self.last_update.isoformat()
        })
        
        # Keep only last 100 entries
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
    
    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get current market regime"""
        return self.current_regime
    
    def is_bull(self) -> bool:
        """Check if market is in bull regime"""
        return self.current_regime == MarketRegime.BULL
    
    def is_bear(self) -> bool:
        """Check if market is in bear regime"""
        return self.current_regime == MarketRegime.BEAR
    
    def is_sideways(self) -> bool:
        """Check if market is in sideways regime"""
        return self.current_regime == MarketRegime.SIDEWAYS
    
    def is_high_volatility(self) -> bool:
        """Check if market is in high volatility regime"""
        return self.current_regime == MarketRegime.HIGH_VOL
    
    def get_regime_description(self) -> str:
        """Get human-readable regime description"""
        if not self.current_regime:
            return "Unknown"
        
        descriptions = {
            MarketRegime.BULL: "Bullish Trend - Favor long positions",
            MarketRegime.BEAR: "Bearish Trend - Favor short positions",
            MarketRegime.SIDEWAYS: "Sideways/Range-bound - Mean reversion strategies",
            MarketRegime.HIGH_VOL: "High Volatility - Reduce position size, use wider stops",
            MarketRegime.EXPIRY_DAY: "Expiry Day - High gamma risk, avoid overnight positions",
            MarketRegime.NEWS_EVENT: "News Event - Elevated uncertainty, wait for clarity"
        }
        
        return descriptions.get(self.current_regime, "Unknown")


# Singleton instance
regime_engine = RegimeEngine()


def get_regime_engine() -> RegimeEngine:
    """Get regime engine instance"""
    return regime_engine
