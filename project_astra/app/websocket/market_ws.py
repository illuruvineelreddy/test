"""
WebSocket Market Data Engine for Project Astra
Handles real-time tick data streaming from Upstox
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any
import redis.asyncio as redis

from configs.settings import settings

logger = logging.getLogger(__name__)


class TickData:
    """Represents a single tick"""
    
    def __init__(
        self,
        symbol: str,
        exchange: str,
        last_price: float,
        volume: int,
        timestamp: datetime,
        bid_price: float = 0.0,
        ask_price: float = 0.0,
        bid_qty: int = 0,
        ask_qty: int = 0,
        open_price: float = 0.0,
        high_price: float = 0.0,
        low_price: float = 0.0,
        close_price: float = 0.0,
        change: float = 0.0,
        change_percent: float = 0.0,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.last_price = last_price
        self.volume = volume
        self.timestamp = timestamp
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.bid_qty = bid_qty
        self.ask_qty = ask_qty
        self.open_price = open_price
        self.high_price = high_price
        self.low_price = low_price
        self.close_price = close_price
        self.change = change
        self.change_percent = change_percent
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'last_price': self.last_price,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat(),
            'bid_price': self.bid_price,
            'ask_price': self.ask_price,
            'bid_qty': self.bid_qty,
            'ask_qty': self.ask_qty,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'close_price': self.close_price,
            'change': self.change,
            'change_percent': self.change_percent,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TickData':
        return cls(
            symbol=data['symbol'],
            exchange=data['exchange'],
            last_price=data['last_price'],
            volume=data['volume'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            bid_price=data.get('bid_price', 0.0),
            ask_price=data.get('ask_price', 0.0),
            bid_qty=data.get('bid_qty', 0),
            ask_qty=data.get('ask_qty', 0),
            open_price=data.get('open_price', 0.0),
            high_price=data.get('high_price', 0.0),
            low_price=data.get('low_price', 0.0),
            close_price=data.get('close_price', 0.0),
            change=data.get('change', 0.0),
            change_percent=data.get('change_percent', 0.0),
        )


class WebSocketEngine:
    """
    Real-time WebSocket Engine for Market Data
    Handles connections, subscriptions, and tick distribution
    """
    
    def __init__(self):
        self.redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        self.redis_client: Optional[redis.Redis] = None
        self.connected = False
        self.subscriptions: Dict[str, bool] = {}
        self.tick_callbacks: List[Callable] = []
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
    async def connect(self) -> bool:
        """Connect to Redis for pub/sub"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            self.connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to Redis for WebSocket pub/sub")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            logger.info("Disconnected from Redis")
    
    def register_callback(self, callback: Callable):
        """Register a callback for tick data"""
        self.tick_callbacks.append(callback)
        logger.info(f"Registered tick callback: {callback.__name__}")
    
    async def publish_tick(self, tick: TickData):
        """Publish tick data to Redis"""
        if not self.connected or not self.redis_client:
            logger.warning("Cannot publish tick: Not connected to Redis")
            return
        
        try:
            tick_data = tick.to_dict()
            tick_json = json.dumps(tick_data)
            
            # Publish to general ticks channel
            await self.redis_client.publish("market_ticks", tick_json)
            
            # Publish to symbol-specific channel
            await self.redis_client.publish(f"ticks:{tick.symbol}", tick_json)
            
            # Store in Redis Stream for replay
            stream_key = f"ticks_stream:{tick.symbol}"
            await self.redis_client.xadd(stream_key, {"data": tick_json})
            
            # Trim stream to last 10000 ticks per symbol
            await self.redis_client.xtrim(stream_key, maxlen=10000)
            
        except Exception as e:
            logger.error(f"Failed to publish tick: {e}")
    
    async def subscribe_to_broker(self, instruments: List[str]) -> bool:
        """
        Subscribe to instruments via broker WebSocket
        This integrates with Upstox WebSocket
        """
        from app.market_data.broker_client import get_upstox_client
        
        client = get_upstox_client()
        
        if not client.configured:
            logger.warning("Broker not configured, using mock data")
            return await self.start_mock_data(instruments)
        
        # Convert symbols to instrument keys
        instrument_keys = []
        for symbol in instruments:
            key = client.get_instrument_key(symbol)
            instrument_keys.append(key)
            self.subscriptions[symbol] = True
        
        # Subscribe via broker
        success = client.subscribe(instrument_keys)
        
        if success:
            logger.info(f"Subscribed to {len(instruments)} instruments")
            return True
        else:
            logger.error("Failed to subscribe to instruments")
            return False
    
    async def start_mock_data(self, symbols: List[str]):
        """Generate mock tick data for testing"""
        import random
        
        logger.info(f"Starting mock data generation for {len(symbols)} symbols")
        
        base_prices = {
            'NIFTY': 22000.0,
            'BANKNIFTY': 47000.0,
            'FINNIFTY': 21000.0,
            'RELIANCE': 2900.0,
            'TCS': 4100.0,
            'INFY': 1600.0,
            'HDFCBANK': 1500.0,
            'ICICIBANK': 1000.0,
        }
        
        while self.connected:
            for symbol in symbols:
                base = base_prices.get(symbol, 1000.0)
                
                # Random walk
                change = random.uniform(-0.001, 0.001)
                price = base * (1 + change)
                
                tick = TickData(
                    symbol=symbol,
                    exchange='NSE',
                    last_price=round(price, 2),
                    volume=random.randint(100, 10000),
                    timestamp=datetime.now(),
                    bid_price=round(price * 0.9995, 2),
                    ask_price=round(price * 1.0005, 2),
                    bid_qty=random.randint(100, 5000),
                    ask_qty=random.randint(100, 5000),
                    open_price=base,
                    high_price=round(base * 1.002, 2),
                    low_price=round(base * 0.998, 2),
                    close_price=base,
                    change=round(price - base, 2),
                    change_percent=round(change * 100, 3),
                )
                
                await self.publish_tick(tick)
                
                # Call registered callbacks
                for callback in self.tick_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(tick)
                        else:
                            callback(tick)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
            
            await asyncio.sleep(1)  # 1 tick per second per symbol
    
    async def listen_for_ticks(self):
        """Listen for ticks from Redis pub/sub"""
        if not self.connected or not self.redis_client:
            return
        
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("market_ticks")
            
            logger.info("Listening for ticks from Redis...")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        tick_data = json.loads(message['data'])
                        tick = TickData.from_dict(tick_data)
                        
                        # Call registered callbacks
                        for callback in self.tick_callbacks:
                            try:
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(tick)
                                else:
                                    callback(tick)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                                
                    except Exception as e:
                        logger.error(f"Error processing tick: {e}")
                        
        except Exception as e:
            logger.error(f"Error listening for ticks: {e}")
    
    async def run_with_reconnect(self, symbols: List[str]):
        """Run WebSocket with auto-reconnect"""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                if not self.connected:
                    success = await self.connect()
                    if not success:
                        self.reconnect_attempts += 1
                        logger.warning(
                            f"Reconnection attempt {self.reconnect_attempts}/"
                            f"{self.max_reconnect_attempts} failed"
                        )
                        await asyncio.sleep(self.reconnect_delay)
                        continue
                
                # Subscribe to instruments
                await self.subscribe_to_broker(symbols)
                
                logger.info("WebSocket engine running...")
                
                # Keep running
                while self.connected:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.connected = False
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts < self.max_reconnect_attempts:
                    logger.warning(
                        f"Attempting reconnect in {self.reconnect_delay}s..."
                    )
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    logger.error("Max reconnection attempts reached")
                    break
        
        logger.error("WebSocket engine stopped")


# Singleton instance
websocket_engine = WebSocketEngine()


def get_websocket_engine() -> WebSocketEngine:
    """Get WebSocket engine instance"""
    return websocket_engine
