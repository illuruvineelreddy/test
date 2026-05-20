"""
Main Trading Orchestrator for Project Astra
Coordinates all engines: WebSocket, Features, Regime, Strategies, Risk, ML, Execution
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

from configs.settings import settings
from app.websocket.market_ws import get_websocket_engine, TickData
from app.feature_engine.feature_calculator import get_feature_engine
from app.regime_engine.regime_detector import get_regime_engine, MarketRegime
from app.strategies.strategy_engine import get_strategy_engine
from app.risk_engine.risk_manager import get_risk_engine
from app.ml_engine.confidence_model import get_ml_confidence_engine
from app.paper_trading.simulator import get_paper_trading_engine
from app.market_data.candle_builder import get_candle_builder

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator that coordinates all trading components
    """
    
    def __init__(self, trading_mode: str = 'paper'):
        self.trading_mode = trading_mode  # 'paper', 'semi_auto', 'full_auto'
        
        # Initialize engines
        self.websocket_engine = get_websocket_engine()
        self.feature_engine = get_feature_engine()
        self.regime_engine = get_regime_engine()
        self.strategy_engine = get_strategy_engine()
        self.risk_engine = get_risk_engine()
        self.ml_engine = get_ml_confidence_engine()
        self.paper_trading = get_paper_trading_engine()
        self.candle_builder = get_candle_builder()
        
        # Trading universe
        self.symbols = settings.TRADING_UNIVERSE
        
        # Data storage
        self.tick_data: Dict[str, List] = {}
        self.candle_data: Dict[str, pd.DataFrame] = {}
        
        # State
        self.is_running = False
        self.current_regime: Optional[MarketRegime] = None
        
        logger.info(f"Trading Orchestrator initialized in {trading_mode} mode")
    
    async def start(self):
        """Start the trading system"""
        logger.info("Starting Trading Orchestrator...")
        
        # Connect WebSocket
        self.websocket_engine.register_callback(self.on_tick)
        
        # Start WebSocket with reconnection
        self.is_running = True
        
        # Run regime detection periodically
        asyncio.create_task(self.periodic_regime_detection())
        
        # Run strategy checks periodically
        asyncio.create_task(self.periodic_strategy_check())
        
        # Run risk monitoring
        asyncio.create_task(self.periodic_risk_check())
        
        # Start WebSocket
        await self.websocket_engine.run_with_reconnect(self.symbols)
    
    async def stop(self):
        """Stop the trading system"""
        logger.info("Stopping Trading Orchestrator...")
        self.is_running = False
        
        # Disconnect WebSocket
        await self.websocket_engine.disconnect()
        
        logger.info("Trading Orchestrator stopped")
    
    async def on_tick(self, tick: TickData):
        """
        Callback for incoming ticks
        This is the main entry point for real-time data
        """
        try:
            symbol = tick.symbol
            
            # Store tick
            if symbol not in self.tick_data:
                self.tick_data[symbol] = []
            self.tick_data[symbol].append(tick.to_dict())
            
            # Keep only last 1000 ticks
            if len(self.tick_data[symbol]) > 1000:
                self.tick_data[symbol] = self.tick_data[symbol][-1000:]
            
            # Build candles
            await self.candle_builder.process_tick(tick)
            
            # Get latest candle
            candle = self.candle_builder.get_latest_candle(symbol, '1m')
            
            if candle:
                # Update candle data
                if symbol not in self.candle_data:
                    self.candle_data[symbol] = pd.DataFrame()
                
                # Add candle to DataFrame (simplified)
                # In production, you'd append properly
                
        except Exception as e:
            logger.error(f"Error processing tick: {e}")
    
    async def periodic_regime_detection(self):
        """Run regime detection every minute"""
        while self.is_running:
            try:
                # Get market data
                nifty_df = self.candle_data.get('NIFTY', pd.DataFrame())
                banknifty_df = self.candle_data.get('BANKNIFTY', pd.DataFrame())
                
                # Get current VIX (would fetch from data source)
                vix = 15.0  # Placeholder
                
                # Detect regime
                self.current_regime = self.regime_engine.detect_regime(
                    nifty_df=nifty_df,
                    banknifty_df=banknifty_df,
                    vix=vix,
                    is_expiry=self._is_expiry_day(),
                    is_news_event=False
                )
                
                logger.info(f"Current regime: {self.current_regime.value}")
                
            except Exception as e:
                logger.error(f"Error in regime detection: {e}")
            
            await asyncio.sleep(60)  # Every minute
    
    async def periodic_strategy_check(self):
        """Check for trading signals every candle close"""
        while self.is_running:
            try:
                for symbol in self.symbols:
                    # Get features
                    df = self.candle_data.get(symbol, pd.DataFrame())
                    
                    if df.empty or len(df) < 50:
                        continue
                    
                    # Calculate features
                    features = self.feature_engine.get_all_features(
                        symbol=symbol,
                        df=df,
                        vix=15.0  # Would fetch real VIX
                    )
                    
                    if not features:
                        continue
                    
                    # Get strategy signals
                    signals = self.strategy_engine.generate_signals(
                        symbol=symbol,
                        df=df,
                        features=features,
                        regime=self.current_regime
                    )
                    
                    # Process signals
                    for signal in signals:
                        await self.process_signal(signal, features)
                
            except Exception as e:
                logger.error(f"Error in strategy check: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def process_signal(self, signal: Dict, features: Dict):
        """Process a trading signal through the full pipeline"""
        try:
            symbol = signal['symbol']
            action = signal['action']
            
            logger.info(f"Processing signal: {action} {symbol}")
            
            # Check risk limits
            risk_ok = self.risk_engine.check_trade_limits(
                symbol=symbol,
                action=action,
                quantity=signal.get('quantity', 0),
                price=signal.get('price', 0)
            )
            
            if not risk_ok:
                logger.warning(f"Trade rejected by risk engine: {symbol}")
                return
            
            # Get ML confidence (if available)
            ml_approved = True
            ml_analysis = {}
            
            if self.ml_engine.is_trained:
                avg_win = signal.get('target', 0) - signal.get('price', 0)
                avg_loss = signal.get('price', 0) - signal.get('stop_loss', 0)
                
                ml_approved, ml_analysis = self.ml_engine.should_execute_trade(
                    features=features,
                    avg_win=avg_win,
                    avg_loss=abs(avg_loss),
                    costs=50  # Estimated costs
                )
                
                if not ml_approved:
                    logger.info(f"Trade filtered by ML: {ml_analysis['reason']}")
                    return
            
            # Execute trade based on mode
            if self.trading_mode == 'paper':
                await self.execute_paper_trade(signal, ml_analysis)
            elif self.trading_mode == 'semi_auto':
                await self.request_manual_approval(signal, ml_analysis)
            elif self.trading_mode == 'full_auto':
                await self.execute_live_trade(signal, ml_analysis)
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
    
    async def execute_paper_trade(self, signal: Dict, ml_analysis: Dict):
        """Execute trade in paper trading mode"""
        try:
            order = self.paper_trading.place_order(
                symbol=signal['symbol'],
                transaction_type='BUY' if signal['action'] == 'BUY' else 'SELL',
                quantity=signal.get('quantity', 1),
                order_type='MARKET',
                price=signal.get('price'),
                strategy=signal.get('strategy', 'UNKNOWN'),
                stop_loss=signal.get('stop_loss'),
                target=signal.get('target')
            )
            
            logger.info(
                f"[PAPER EXECUTION] {signal['action']} {signal.get('quantity', 1)} "
                f"{signal['symbol']} | ML Confidence: {ml_analysis.get('win_probability', 0):.2%}"
            )
            
        except Exception as e:
            logger.error(f"Paper trade execution failed: {e}")
    
    async def request_manual_approval(self, signal: Dict, ml_analysis: Dict):
        """Request manual approval for semi-auto mode"""
        logger.info(
            f"[MANUAL APPROVAL REQUIRED] {signal['action']} {signal['symbol']} | "
            f"ML: {ml_analysis.get('win_probability', 0):.2%} | "
            f"EV: {ml_analysis.get('expected_value', 0):.2f}"
        )
        # In production, send notification via Telegram/Email
    
    async def execute_live_trade(self, signal: Dict, ml_analysis: Dict):
        """Execute live trade (requires broker integration)"""
        from app.market_data.broker_client import get_upstox_client
        
        client = get_upstox_client()
        
        if not client.configured:
            logger.error("Cannot execute live trade: Broker not configured")
            return
        
        # Place order via broker
        order = client.place_order(
            symbol=signal['symbol'],
            transaction_type='BUY' if signal['action'] == 'BUY' else 'SELL',
            product_type='INTRADAY',
            order_type='MARKET',
            quantity=signal.get('quantity', 1),
            price=signal.get('price')
        )
        
        logger.info(
            f"[LIVE EXECUTION] {signal['action']} {signal.get('quantity', 1)} "
            f"{signal['symbol']} | Order ID: {order.get('order_id')} | "
            f"ML: {ml_analysis.get('win_probability', 0):.2%}"
        )
    
    async def periodic_risk_check(self):
        """Monitor risk metrics continuously"""
        while self.is_running:
            try:
                # Get portfolio summary
                if self.trading_mode == 'paper':
                    summary = self.paper_trading.get_portfolio_summary()
                    
                    # Check daily loss limit
                    if summary['total_pnl'] < -settings.MAX_DAILY_LOSS:
                        logger.critical("DAILY LOSS LIMIT EXCEEDED - STOPPING TRADING")
                        self.risk_engine.trigger_kill_switch("Daily loss limit exceeded")
                        break
                
                # Log risk metrics
                exposure = self.risk_engine.get_exposure_summary()
                logger.debug(f"Risk exposure: {exposure}")
                
            except Exception as e:
                logger.error(f"Error in risk check: {e}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
    
    def _is_expiry_day(self) -> bool:
        """Check if today is options expiry day"""
        # NIFTY/BANKNIFTY expiry: Thursday
        # FINNIFTY expiry: Tuesday and Friday
        import calendar
        today = datetime.now().weekday()
        return today == calendar.THURSDAY  # Simplified
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            'is_running': self.is_running,
            'trading_mode': self.trading_mode,
            'current_regime': self.current_regime.value if self.current_regime else None,
            'symbols_monitored': self.symbols,
            'regime_description': self.regime_engine.get_regime_description() if self.current_regime else None
        }


# Singleton instance
orchestrator: Optional[TradingOrchestrator] = None


def get_orchestrator(trading_mode: str = 'paper') -> TradingOrchestrator:
    """Get orchestrator instance"""
    global orchestrator
    if orchestrator is None:
        orchestrator = TradingOrchestrator(trading_mode=trading_mode)
    return orchestrator
