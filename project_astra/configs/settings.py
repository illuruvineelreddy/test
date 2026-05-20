"""
Configuration settings for Project Astra
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "Project Astra"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database - PostgreSQL with TimescaleDB
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/astra_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: str = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    
    # WebSocket Settings
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_RECONNECT_DELAY: int = 5  # seconds
    WS_MAX_RECONNECT_ATTEMPTS: int = 10
    
    # Market Data
    DATA_SOURCE: str = "zerodha"  # zerodha, upstox, fyers, angelone, truedata
    MARKET_TICK_CHANNEL: str = "market_ticks"
    MARKET_CANDLE_CHANNEL: str = "market_candles"
    
    # Broker Configuration - Upstox
    UPSTOX_API_KEY: Optional[str] = None
    UPSTOX_API_SECRET: Optional[str] = None
    UPSTOX_ACCESS_TOKEN: Optional[str] = None
    UPSTOX_ENVIRONMENT: str = "live"  # live, test
    
    # Legacy Broker Configuration (for backward compatibility)
    BROKER_API_KEY: Optional[str] = None
    BROKER_API_SECRET: Optional[str] = None
    BROKER_ACCESS_TOKEN: Optional[str] = None
    
    # Trading Mode
    TRADING_MODE: str = "paper"  # paper, semi_auto, full_auto
    PAPER_TRADING_ENABLED: bool = True
    
    # Capital & Risk
    INITIAL_CAPITAL: float = 100000.0  # ₹1 lakh
    RISK_PER_TRADE_PCT: float = 1.0  # 1%
    DAILY_LOSS_LIMIT_PCT: float = 3.0  # 3%
    MAX_CONSECUTIVE_LOSSES: int = 5
    MAX_POSITIONS: int = 5
    MAX_LEVERAGE: float = 2.0
    
    # Order Settings
    DEFAULT_ORDER_TYPE: str = "LIMIT"  # LIMIT, MARKET, SL, SL-M
    ORDER_VALIDITY: str = "DAY"  # DAY, IOC
    MAX_SLIPPAGE_PCT: float = 0.5  # 0.5%
    MIN_LIQUIDITY_QTY: int = 1000  # Minimum lots available
    
    # Strategy Settings
    ENABLED_STRATEGIES: List[str] = [
        "ema_trend",
        "vwap_mean_reversion",
        "momentum_breakout",
    ]
    STRATEGYCooldown_SECONDS: int = 300  # 5 minutes between same strategy signals
    
    # ML Settings
    ML_MODEL_PATH: str = "models/"
    ML_CONFIDENCE_THRESHOLD: float = 0.6  # Minimum confidence to execute
    ML_RETRAIN_FREQUENCY: str = "weekly"  # daily, weekly, monthly
    ML_FEATURE_WINDOW: int = 60  # Number of candles for features
    
    # Regime Detection
    REGIME_UPDATE_INTERVAL: int = 60  # seconds
    VIX_HIGH_THRESHOLD: float = 20.0
    VIX_LOW_THRESHOLD: float = 12.0
    
    # Technical Indicators
    EMA_FAST: int = 20
    EMA_SLOW: int = 50
    RSI_PERIOD: int = 14
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0
    ATR_PERIOD: int = 14
    VWAP_PERIOD: int = 20
    
    # Options Settings
    OPTIONS_STRIKE_RANGE: int = 5  # Number of strikes either side
    OPTIONS_EXPIRY_DAYS_THRESHOLD: int = 7  # Only trade weekly options within 7 days
    MIN_OPTIONS_OI: int = 10000  # Minimum open interest in lots
    
    # Backtesting
    BACKTEST_START_DATE: str = "2020-01-01"
    BACKTEST_END_DATE: str = "2024-12-31"
    BACKTEST_INITIAL_CAPITAL: float = 100000.0
    BACKTEST_INCLUDE_CHARGES: bool = True
    
    # Charges (India)
    BROKERAGE_PER_ORDER: float = 20.0  # ₹20 per order
    STT_EQUITY_BUY: float = 0.0  # 0% on equity buy
    STT_EQUITY_SELL: float = 0.1 / 100  # 0.1% on equity sell
    STT_OPTIONS_SELL: float = 0.167 / 100  # 0.167% on options sell
    GST_PCT: float = 18.0  # 18% GST on brokerage
    EXCHANGE_CHARGES_NFO: float = 0.00325 / 100  # NSE F&O charges
    SEBI_CHARGES: float = 10.0 / 100000000  # ₹10 per crore
    STAMP_DUTY_BUY: float = 0.003 / 100  # 0.003% on buy
    STAMP_DUTY_SELL: float = 0.03 / 100  # 0.03% on sell
    
    # Monitoring & Alerts
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    ALERT_ON_TRADE: bool = True
    ALERT_ON_KILL_SWITCH: bool = True
    ALERT_ON_DAILY_LOSS: bool = True
    ALERT_ON_DISCONNECTION: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE: str = "logs/astra.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    # Performance
    CACHE_TTL_SECONDS: int = 60
    BATCH_SIZE: int = 100
    WORKER_COUNT: int = 4
    
    # Reconciliation
    RECONCILIATION_INTERVAL: int = 60  # seconds
    RECONCILIATION_TOLERANCE: float = 0.01  # 1% tolerance
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
