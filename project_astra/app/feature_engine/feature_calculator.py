"""
Feature Engine for Project Astra
Calculates technical indicators, options features, and market features
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np
import pandas_ta as ta

logger = logging.getLogger(__name__)


class FeatureEngine:
    """
    Calculates real-time features for ML models and strategies
    """
    
    def __init__(self):
        self.feature_cache: Dict[str, Dict] = {}
        
    def calculate_technical_features(
        self, 
        df: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """
        Calculate technical indicators from OHLCV data
        
        Args:
            df: DataFrame with columns [open, high, low, close, volume]
            symbol: Symbol name
            
        Returns:
            Dictionary of feature names and values
        """
        if df.empty or len(df) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            return {}
        
        features = {}
        
        try:
            # Moving Averages
            features['ema_9'] = ta.ema(df['close'], length=9).iloc[-1]
            features['ema_20'] = ta.ema(df['close'], length=20).iloc[-1]
            features['ema_50'] = ta.ema(df['close'], length=50).iloc[-1]
            features['sma_20'] = ta.sma(df['close'], length=20).iloc[-1]
            features['sma_50'] = ta.sma(df['close'], length=50).iloc[-1]
            features['sma_200'] = ta.sma(df['close'], length=200).iloc[-1] if len(df) >= 200 else np.nan
            
            # EMA Gap (trend strength)
            features['ema_gap'] = (features['ema_20'] - features['ema_50']) / features['ema_50'] * 100
            
            # RSI
            features['rsi_14'] = ta.rsi(df['close'], length=14).iloc[-1]
            
            # MACD
            macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
            features['macd'] = macd['MACD_12_26_9'].iloc[-1]
            features['macd_signal'] = macd['MACDs_12_26_9'].iloc[-1]
            features['macd_hist'] = macd['MACDh_12_26_9'].iloc[-1]
            
            # Bollinger Bands
            bbands = ta.bbands(df['close'], length=20, std=2)
            features['bb_upper'] = bbands['BBU_20_2.0'].iloc[-1]
            features['bb_lower'] = bbands['BBL_20_2.0'].iloc[-1]
            features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / features['bb_lower'] * 100
            
            # Position within bands
            current_close = df['close'].iloc[-1]
            features['bb_position'] = (current_close - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
            
            # ATR (volatility)
            features['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            features['atr_percent'] = features['atr_14'] / current_close * 100
            
            # VWAP (if available in data)
            if 'vwap' in df.columns:
                features['vwap'] = df['vwap'].iloc[-1]
            else:
                # Calculate approximate VWAP
                typical_price = (df['high'] + df['low'] + df['close']) / 3
                features['vwap'] = (typical_price * df['volume']).rolling(window=20).sum().iloc[-1] / df['volume'].rolling(window=20).sum().iloc[-1]
            
            # VWAP distance
            features['vwap_distance'] = (current_close - features['vwap']) / features['vwap'] * 100
            
            # Volume features
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            features['volume_ratio'] = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Price momentum
            features['momentum_5'] = df['close'].pct_change(5).iloc[-1] * 100
            features['momentum_10'] = df['close'].pct_change(10).iloc[-1] * 100
            
            # ADX (trend strength)
            adx = ta.adx(df['high'], df['low'], df['close'], length=14)
            features['adx'] = adx['ADX_14'].iloc[-1]
            
            # Stochastic
            stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3)
            features['stoch_k'] = stoch['STOCHk_14_3_3'].iloc[-1]
            features['stoch_d'] = stoch['STOCHd_14_3_3'].iloc[-1]
            
            # CCI
            features['cci'] = ta.cci(df['high'], df['low'], df['close'], length=20).iloc[-1]
            
            # WillR
            features['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14).iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating technical features for {symbol}: {e}")
            return {}
        
        # Clean NaN values
        features = {k: (v if not pd.isna(v) else 0.0) for k, v in features.items()}
        
        return features
    
    def calculate_options_features(
        self,
        option_chain: Dict[str, Any],
        underlying_price: float,
        vix: float
    ) -> Dict[str, float]:
        """
        Calculate options-specific features
        
        Args:
            option_chain: Dict with CE and PE data
            underlying_price: Current price of underlying
            vix: India VIX value
            
        Returns:
            Dictionary of options features
        """
        features = {}
        
        try:
            # Extract ATM strike
            atm_strike = round(underlying_price / 50) * 50
            
            # Get ATM CE and PE data
            atm_ce = option_chain.get('CE', {}).get(atm_strike, {})
            atm_pe = option_chain.get('PE', {}).get(atm_strike, {})
            
            # Implied Volatility
            ce_iv = atm_ce.get('iv', 0)
            pe_iv = atm_pe.get('iv', 0)
            features['atm_ce_iv'] = ce_iv
            features['atm_pe_iv'] = ce_iv
            features['avg_iv'] = (ce_iv + pe_iv) / 2
            
            # IV Rank (simplified - would need 52-week high/low IV)
            features['iv_rank'] = min(max((ce_iv - 10) / (40 - 10), 0), 1)  # Placeholder
            
            # Open Interest
            ce_oi = atm_ce.get('oi', 0)
            pe_oi = atm_pe.get('oi', 0)
            features['atm_ce_oi'] = ce_oi
            features['atm_pe_oi'] = pe_oi
            
            # OI Change
            ce_oi_change = atm_ce.get('oi_change', 0)
            pe_oi_change = atm_pe.get('oi_change', 0)
            features['ce_oi_change'] = ce_oi_change
            features['pe_oi_change'] = pe_oi_change
            
            # Put-Call Ratio (PCR)
            total_ce_oi = sum(v.get('oi', 0) for v in option_chain.get('CE', {}).values())
            total_pe_oi = sum(v.get('oi', 0) for v in option_chain.get('PE', {}).values())
            features['pcr'] = total_pe_oi / total_ce_oi if total_ce_oi > 0 else 1.0
            
            # PCR OI Change
            total_ce_oi_change = sum(v.get('oi_change', 0) for v in option_chain.get('CE', {}).values())
            total_pe_oi_change = sum(v.get('oi_change', 0) for v in option_chain.get('PE', {}).values())
            features['pcr_change'] = total_pe_oi_change / total_ce_oi_change if total_ce_oi_change > 0 else 1.0
            
            # Max Pain (simplified)
            features['max_pain'] = atm_strike  # Would need full calculation
            
            # Gamma exposure (simplified)
            features['gamma_exposure'] = (ce_oi - pe_oi) / (ce_oi + pe_oi) if (ce_oi + pe_oi) > 0 else 0
            
            # Skew
            features['iv_skew'] = pe_iv - ce_iv
            
        except Exception as e:
            logger.error(f"Error calculating options features: {e}")
            return {}
        
        return features
    
    def calculate_market_features(
        self,
        nifty_df: pd.DataFrame,
        banknifty_df: pd.DataFrame,
        vix: float,
        advance_decline: Dict[str, int]
    ) -> Dict[str, float]:
        """
        Calculate broad market features
        
        Args:
            nifty_df: NIFTY 50 OHLCV data
            banknifty_df: BANKNIFTY OHLCV data
            vix: India VIX value
            advance_decline: Dict with 'advance' and 'decline' counts
            
        Returns:
            Dictionary of market-wide features
        """
        features = {}
        
        try:
            # VIX features
            features['vix'] = vix
            features['vix_change'] = 0.0  # Would need previous VIX
            
            # Market breadth
            advances = advance_decline.get('advance', 0)
            declines = advance_decline.get('decline', 0)
            total = advances + declines
            
            features['advance_decline_ratio'] = advances / declines if declines > 0 else advances
            features['breadth'] = (advances - declines) / total if total > 0 else 0
            
            # Sector strength (would need sector indices)
            # Placeholder
            features['sector_strength'] = 0.0
            
            # Relative strength
            if len(nifty_df) > 0 and len(banknifty_df) > 0:
                nifty_return = nifty_df['close'].pct_change(5).iloc[-1] if len(nifty_df) > 5 else 0
                banknifty_return = banknifty_df['close'].pct_change(5).iloc[-1] if len(banknifty_df) > 5 else 0
                features['relative_strength'] = banknifty_return - nifty_return
            else:
                features['relative_strength'] = 0.0
            
            # Market trend
            if len(nifty_df) >= 50:
                nifty_ema20 = ta.ema(nifty_df['close'], length=20).iloc[-1]
                nifty_ema50 = ta.ema(nifty_df['close'], length=50).iloc[-1]
                features['market_trend'] = 1 if nifty_ema20 > nifty_ema50 else -1
            else:
                features['market_trend'] = 0
            
        except Exception as e:
            logger.error(f"Error calculating market features: {e}")
            return {}
        
        return features
    
    def get_all_features(
        self,
        symbol: str,
        df: pd.DataFrame,
        option_chain: Optional[Dict] = None,
        underlying_price: Optional[float] = None,
        vix: Optional[float] = None,
        nifty_df: Optional[pd.DataFrame] = None,
        banknifty_df: Optional[pd.DataFrame] = None,
        advance_decline: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Get all features for a symbol
        
        Returns:
            Complete feature dictionary
        """
        all_features = {}
        
        # Technical features
        tech_features = self.calculate_technical_features(df, symbol)
        all_features.update(tech_features)
        
        # Options features (if applicable)
        if option_chain and underlying_price and vix:
            opt_features = self.calculate_options_features(option_chain, underlying_price, vix)
            all_features.update(opt_features)
        
        # Market features
        if vix is not None:
            market_features = self.calculate_market_features(
                nifty_df=nifty_df or df,
                banknifty_df=banknifty_df or df,
                vix=vix,
                advance_decline=advance_decline or {'advance': 0, 'decline': 0}
            )
            all_features.update(market_features)
        
        # Cache features
        self.feature_cache[symbol] = {
            'features': all_features,
            'timestamp': datetime.now()
        }
        
        return all_features
    
    def get_cached_features(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get cached features for a symbol"""
        cached = self.feature_cache.get(symbol)
        if cached:
            return cached['features']
        return None


# Singleton instance
feature_engine = FeatureEngine()


def get_feature_engine() -> FeatureEngine:
    """Get feature engine instance"""
    return feature_engine
