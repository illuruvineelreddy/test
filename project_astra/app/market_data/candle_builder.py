"""
Candle Builder - Aggregates ticks into OHLCV candles
Supports multiple timeframes: 1m, 5m, 15m, 1h, 1D
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import redis
import json
from loguru import logger

from configs.settings import settings


@dataclass
class Candle:
    """Represents a single candle"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float = 0.0
    trades: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'vwap': self.vwap,
            'trades': self.trades
        }


class CandleBuilder:
    """
    Builds candles from tick data in real-time
    Maintains separate candles for each symbol and timeframe
    """
    
    SUPPORTED_TIMEFRAMES = ['1m', '5m', '15m', '1h', '1D']
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        
        # Current active candles: {(symbol, timeframe, timestamp): Candle}
        self.active_candles: Dict[tuple, Candle] = {}
        
        # Tick aggregation buffers
        self.tick_buffers: Dict[tuple, List[dict]] = {}
        
        logger.info("CandleBuilder initialized")
    
    def _get_time_bucket(self, timestamp: datetime, timeframe: str) -> datetime:
        """
        Get the start time of the candle bucket for given timestamp
        
        Examples:
        - 1m: rounds down to nearest minute
        - 5m: rounds down to nearest 5 minutes
        - 1h: rounds down to nearest hour
        """
        if timeframe == '1m':
            return timestamp.replace(second=0, microsecond=0)
        elif timeframe == '5m':
            minute = (timestamp.minute // 5) * 5
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '15m':
            minute = (timestamp.minute // 15) * 15
            return timestamp.replace(minute=minute, second=0, microsecond=0)
        elif timeframe == '1h':
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif timeframe == '1D':
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    def process_tick(self, tick: dict) -> List[Candle]:
        """
        Process a single tick and update all relevant candles
        
        Args:
            tick: Dictionary with keys: symbol, price, volume, timestamp
            
        Returns:
            List of completed candles (if any)
        """
        completed_candles = []
        symbol = tick.get('symbol')
        timestamp = datetime.fromisoformat(tick['timestamp'].replace('Z', '+00:00'))
        price = float(tick['price'])
        volume = int(tick.get('volume', 0))
        
        if not symbol:
            logger.warning(f"Tick missing symbol: {tick}")
            return completed_candles
        
        # Update candles for all supported timeframes
        for timeframe in self.SUPPORTED_TIMEFRAMES:
            candle_key = self._get_time_bucket(timestamp, timeframe)
            candle_id = (symbol, timeframe, candle_key)
            
            if candle_id not in self.active_candles:
                # Create new candle
                new_candle = Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=candle_key,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=volume,
                    vwap=price,
                    trades=1
                )
                self.active_candles[candle_id] = new_candle
                logger.debug(f"New candle created: {symbol} {timeframe} @ {candle_key}")
            else:
                # Update existing candle
                candle = self.active_candles[candle_id]
                candle.high = max(candle.high, price)
                candle.low = min(candle.low, price)
                candle.close = price
                candle.volume += volume
                candle.trades += 1
                
                # Update VWAP
                total_volume = candle.volume
                if total_volume > 0:
                    # Simplified VWAP: running average
                    candle.vwap = (
                        (candle.vwap * (total_volume - volume) + price * volume) 
                        / total_volume
                    )
        
        # Check for completed candles
        completed_candles = self._check_completed_candles()
        
        # Publish updated candles to Redis
        for candle in completed_candles:
            self._publish_candle(candle)
        
        return completed_candles
    
    def _check_completed_candles(self) -> List[Candle]:
        """
        Check which candles have completed based on current time
        Returns list of completed candles and removes them from active set
        """
        completed = []
        now = datetime.utcnow()
        
        candles_to_remove = []
        
        for candle_id, candle in self.active_candles.items():
            symbol, timeframe, timestamp = candle_id
            
            # Calculate when this candle should end
            if timeframe == '1m':
                candle_end = timestamp + timedelta(minutes=1)
            elif timeframe == '5m':
                candle_end = timestamp + timedelta(minutes=5)
            elif timeframe == '15m':
                candle_end = timestamp + timedelta(minutes=15)
            elif timeframe == '1h':
                candle_end = timestamp + timedelta(hours=1)
            elif timeframe == '1D':
                candle_end = timestamp + timedelta(days=1)
            else:
                continue
            
            # If current time is past candle end + small buffer, candle is complete
            if now >= candle_end + timedelta(seconds=5):
                completed.append(candle)
                candles_to_remove.append(candle_id)
                logger.debug(f"Candle completed: {candle.symbol} {candle.timeframe} @ {candle.timestamp}")
        
        # Remove completed candles
        for candle_id in candles_to_remove:
            del self.active_candles[candle_id]
        
        return completed
    
    def _publish_candle(self, candle: Candle):
        """Publish completed candle to Redis stream"""
        try:
            channel = f"candle:{candle.symbol}:{candle.timeframe}"
            candle_data = json.dumps(candle.to_dict())
            
            # Publish to Redis Pub/Sub
            self.redis_client.publish(channel, candle_data)
            
            # Also add to Redis Stream for persistence
            stream_key = f"candles:{candle.timeframe}"
            self.redis_client.xadd(
                stream_key,
                {
                    'symbol': candle.symbol,
                    'data': candle_data
                },
                maxlen=10000  # Keep last 10k candles per timeframe
            )
            
            logger.trace(f"Published candle: {candle.symbol} {candle.timeframe}")
            
        except Exception as e:
            logger.error(f"Error publishing candle: {e}")
    
    def get_current_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Get the current active candle for a symbol/timeframe"""
        now = datetime.utcnow()
        bucket = self._get_time_bucket(now, timeframe)
        candle_id = (symbol, timeframe, bucket)
        
        return self.active_candles.get(candle_id)
    
    def get_historical_candles(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int = 100
    ) -> List[Candle]:
        """
        Retrieve historical candles from database
        This would typically query PostgreSQL/TimescaleDB
        For now, returns empty list (to be implemented)
        """
        # TODO: Implement database query
        logger.debug(f"Fetching {count} historical candles for {symbol} {timeframe}")
        return []


# Singleton instance
candle_builder = CandleBuilder()
