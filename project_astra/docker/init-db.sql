-- Database initialization script for Project Astra
-- Creates tables for ticks, candles, trades, features, and models

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Table: ticks (raw tick data)
CREATE TABLE IF NOT EXISTS ticks (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    price DECIMAL(18, 4) NOT NULL,
    volume BIGINT,
    bid_price DECIMAL(18, 4),
    ask_price DECIMAL(18, 4),
    bid_qty BIGINT,
    ask_qty BIGINT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('ticks', 'timestamp', if_not_exists => TRUE);

-- Indexes for ticks
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ticks_time ON ticks (timestamp DESC);

-- Table: candles (OHLCV data)
CREATE TABLE IF NOT EXISTS candles (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    open DECIMAL(18, 4) NOT NULL,
    high DECIMAL(18, 4) NOT NULL,
    low DECIMAL(18, 4) NOT NULL,
    close DECIMAL(18, 4) NOT NULL,
    volume BIGINT,
    vwap DECIMAL(18, 4),
    trades INTEGER,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('candles', 'timestamp', if_not_exists => TRUE);

-- Indexes for candles
CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe_time ON candles (symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_candles_time ON candles (timestamp DESC);

-- Table: trades (trade history)
CREATE TABLE IF NOT EXISTS trades (
    trade_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    strategy VARCHAR(100),
    side VARCHAR(10) NOT NULL, -- LONG or SHORT
    quantity BIGINT NOT NULL,
    entry_price DECIMAL(18, 4) NOT NULL,
    entry_time TIMESTAMPTZ NOT NULL,
    exit_price DECIMAL(18, 4),
    exit_time TIMESTAMPTZ,
    stop_loss DECIMAL(18, 4),
    target_price DECIMAL(18, 4),
    pnl DECIMAL(18, 2),
    pnl_pct DECIMAL(10, 4),
    charges DECIMAL(18, 2),
    net_pnl DECIMAL(18, 2),
    status VARCHAR(20) DEFAULT 'open', -- open, closed, cancelled
    ml_confidence DECIMAL(5, 4),
    regime VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for trades
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades (status);

-- Table: features (calculated features for ML)
CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    rsi DECIMAL(10, 4),
    ema_20 DECIMAL(18, 4),
    ema_50 DECIMAL(18, 4),
    sma_20 DECIMAL(18, 4),
    sma_50 DECIMAL(18, 4),
    macd DECIMAL(18, 4),
    macd_signal DECIMAL(18, 4),
    bollinger_upper DECIMAL(18, 4),
    bollinger_lower DECIMAL(18, 4),
    atr DECIMAL(18, 4),
    vwap DECIMAL(18, 4),
    iv_rank DECIMAL(10, 4),
    oi_change BIGINT,
    pcr DECIMAL(10, 4),
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('features', 'timestamp', if_not_exists => TRUE);

-- Indexes for features
CREATE INDEX IF NOT EXISTS idx_features_symbol_timeframe_time ON features (symbol, timeframe, timestamp DESC);

-- Table: models (ML model registry)
CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(50), -- xgboost, lightgbm, etc.
    accuracy DECIMAL(10, 4),
    precision DECIMAL(10, 4),
    recall DECIMAL(10, 4),
    f1_score DECIMAL(10, 4),
    sharpe_ratio DECIMAL(10, 4),
    max_drawdown DECIMAL(10, 4),
    training_start TIMESTAMPTZ,
    training_end TIMESTAMPTZ,
    training_data_start DATE,
    training_data_end DATE,
    feature_importance JSONB,
    model_path VARCHAR(500),
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint on model name and version
CREATE UNIQUE INDEX IF NOT EXISTS idx_models_name_version ON models (model_name, version);

-- Table: risk_logs (risk engine decisions)
CREATE TABLE IF NOT EXISTS risk_logs (
    id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(100),
    symbol VARCHAR(50),
    decision VARCHAR(20), -- approved, rejected
    reason TEXT,
    position_size BIGINT,
    max_loss DECIMAL(18, 2),
    risk_level VARCHAR(20),
    capital_at_time DECIMAL(18, 2),
    exposure_at_time DECIMAL(18, 2),
    kill_switch_active BOOLEAN,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for risk logs
CREATE INDEX IF NOT EXISTS idx_risk_logs_trade_id ON risk_logs (trade_id);
CREATE INDEX IF NOT EXISTS idx_risk_logs_timestamp ON risk_logs (timestamp DESC);

-- Table: system_events (system monitoring)
CREATE TABLE IF NOT EXISTS system_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20), -- info, warning, error, critical
    message TEXT,
    details JSONB,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Index for system events
CREATE INDEX IF NOT EXISTS idx_system_events_type_time ON system_events (event_type, timestamp DESC);

-- Create view for active positions
CREATE OR REPLACE VIEW active_positions AS
SELECT 
    trade_id,
    symbol,
    strategy,
    side,
    quantity,
    entry_price,
    entry_time,
    stop_loss,
    target_price,
    current_price,
    unrealized_pnl,
    regime,
    timestamp
FROM trades
WHERE status = 'open';

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

COMMENT ON TABLE ticks IS 'Raw tick data from market data feeds';
COMMENT ON TABLE candles IS 'Aggregated OHLCV candle data';
COMMENT ON TABLE trades IS 'Trade execution history';
COMMENT ON TABLE features IS 'Calculated technical and options features';
COMMENT ON TABLE models IS 'ML model registry and performance tracking';
COMMENT ON TABLE risk_logs IS 'Risk engine decision logs';
COMMENT ON TABLE system_events IS 'System monitoring and alert events';
