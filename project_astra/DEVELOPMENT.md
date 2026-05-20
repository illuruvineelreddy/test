# Project Astra - Development & Usage Guide

## Quick Start

### 1. Clone and Setup

```bash
cd project_astra

# Copy environment file
cp .env.example .env

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

**Note**: TA-Lib requires the underlying C library to be installed first:
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib

# macOS
brew install ta-lib

# Or use the pure Python alternative (already in requirements)
pip install pandas-ta
```

### 2. Start Infrastructure with Docker

```bash
# Start PostgreSQL, TimescaleDB, and Redis
docker-compose up -d db redis

# Wait for services to be healthy
docker-compose ps

# View logs
docker-compose logs -f db
docker-compose logs -f redis
```

### 3. Run Database Migrations

```bash
# The database is initialized automatically via docker/init-db.sql
# To manually verify:
docker exec -it astra_db psql -U postgres -d astra_db -c "\dt"
```

### 4. Start the Application

```bash
# Option A: Run directly
python -m app.main

# Option B: Use uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Option C: Run with Docker Compose (all services)
docker-compose up
```

### 5. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Celery Flower** (monitoring): http://localhost:5555

---

## Architecture Overview

### Data Flow

```
Broker WebSocket → Market Data Engine → Candle Builder → Feature Engine
                                              ↓
                                    Regime Detector
                                              ↓
                                    Strategy Engine
                                              ↓
                                    ML Confidence
                                              ↓
                                    Risk Engine
                                              ↓
                                    Execution Engine
                                              ↓
                                    Broker API
```

### Key Components

#### 1. Market Data (`app/market_data/`)
- Real-time tick ingestion via WebSocket
- Candle aggregation (1m, 5m, 15m, 1h, 1D)
- Redis pub/sub for distribution

#### 2. Feature Engine (`app/feature_engine/`)
- Technical indicators (EMA, RSI, MACD, Bollinger Bands, ATR, VWAP)
- Options features (IV, OI, PCR, Greeks)
- Market regime features

#### 3. Regime Engine (`app/regime_engine/`)
- Detects market state: BULL, BEAR, SIDEWAYS, HIGH_VOL
- Uses rule-based logic initially
- Will evolve to ML-based detection

#### 4. Strategy Engine (`app/strategies/`)
- **EMA Trend Following**: Crossover + momentum confirmation
- **VWAP Mean Reversion**: Fade extreme deviations
- **Momentum Breakout**: Volume-backed breakouts

#### 5. Risk Engine (`app/risk_engine/`)
- Position sizing (1% risk per trade)
- Daily loss limits (3%)
- Kill switch mechanisms
- Real-time exposure monitoring

#### 6. ML Engine (`app/ml_engine/`)
- XGBoost/LightGBM for trade confidence scoring
- SHAP for explainability
- Walk-forward validation

---

## Configuration

Edit `.env` file to customize:

```bash
# Trading Mode
TRADING_MODE=paper  # paper, semi_auto, full_auto

# Capital & Risk
INITIAL_CAPITAL=100000
RISK_PER_TRADE_PCT=1.0
DAILY_LOSS_LIMIT_PCT=3.0

# Broker Credentials (for live trading)
BROKER_API_KEY=your_key
BROKER_API_SECRET=your_secret

# Telegram Alerts (optional)
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## API Endpoints

### Risk Management
- `GET /api/v1/risk/summary` - Current risk exposure
- `GET /api/v1/risk/health` - Check if trading is allowed
- `POST /api/v1/risk/kill-switch/activate` - Activate kill switch
- `POST /api/v1/risk/kill-switch/deactivate` - Deactivate kill switch

### Positions & Capital
- `GET /api/v1/positions` - Active positions
- `GET /api/v1/capital` - Capital and PnL info

### System
- `GET /api/v1/strategies` - Available strategies
- `GET /api/v1/settings` - Current settings
- `GET /health` - Health check

---

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Test specific module
pytest tests/test_risk_engine.py -v
```

---

## Development Workflow

### 1. Add a New Strategy

```python
# app/strategies/my_strategy.py
from app.strategies.strategy_engine import Signal, SignalType

class MyStrategy:
    def __init__(self):
        self.name = "my_strategy"
    
    def generate_signal(self, symbol, candles, regime, current_price):
        # Your logic here
        if buy_condition:
            return Signal(
                symbol=symbol,
                strategy=self.name,
                signal_type=SignalType.LONG,
                entry_price=current_price,
                stop_loss=...,
                target_price=...,
                confidence=0.75,
                timeframe='5m',
                timestamp=datetime.utcnow(),
                metadata={}
            )
        return None

# Register in strategy_engine.py
STRATEGIES['my_strategy'] = MyStrategy()
```

### 2. Add a New Feature

```python
# app/feature_engine/indicators.py
def calculate_my_feature(data):
    # Your calculation
    return feature_value

# Store in database
# app/feature_engine/feature_store.py
feature_store.save(symbol, timeframe, {'my_feature': value})
```

### 3. Backtest a Strategy

```python
# notebooks/backtest_example.ipynb
from app.backtesting.engine import Backtester
from app.strategies.strategy_engine import get_strategy

strategy = get_strategy('ema_trend')
backtester = Backtester(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2024-12-31',
    initial_capital=100000
)

results = backtester.run(symbol='NIFTY')
print(results.summary())
```

---

## Monitoring

### Logs
```bash
# View application logs
tail -f logs/astra.log

# View Docker logs
docker-compose logs -f app
```

### Metrics
- Celery Flower: http://localhost:5555
- Prometheus metrics (future): http://localhost:9090

### Database Queries
```bash
docker exec -it astra_db psql -U postgres -d astra_db

# Recent trades
SELECT * FROM trades ORDER BY entry_time DESC LIMIT 10;

# Active positions
SELECT * FROM active_positions;

# Risk logs
SELECT * FROM risk_logs ORDER BY timestamp DESC LIMIT 10;
```

---

## Production Deployment

### AWS EC2 (Mumbai Region)

1. Launch EC2 instance (t3.medium or higher)
2. Install Docker & Docker Compose
3. Clone repository
4. Configure `.env` for production
5. Set up SSL with Nginx
6. Configure security groups
7. Set up CloudWatch logging
8. Enable automatic backups

### Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use environment variables for sensitive data
- [ ] Enable HTTPS
- [ ] Restrict CORS origins
- [ ] Set up VPC for database
- [ ] Enable encryption at rest
- [ ] Implement rate limiting
- [ ] Set up monitoring alerts

---

## Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker-compose ps db

# Verify connection
docker exec -it astra_db psql -U postgres -d astra_db -c "SELECT 1;"

# Check logs
docker-compose logs db
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# For TA-Lib issues
pip uninstall ta-lib
pip install pandas-ta  # Pure Python alternative
```

---

## Next Steps

### Phase 0 (Current)
- ✅ Project structure
- ✅ Configuration system
- ✅ Candle builder
- ✅ Risk engine
- ✅ Strategy engine (basic)
- ✅ API endpoints
- ✅ Docker setup

### Phase 1 (Next)
- [ ] WebSocket market data integration
- [ ] Feature engine implementation
- [ ] Regime detector
- [ ] Paper trading engine
- [ ] Reconciliation system
- [ ] Dashboard UI

### Phase 2
- [ ] ML model training pipeline
- [ ] XGBoost integration
- [ ] SHAP explainability
- [ ] Walk-forward testing
- [ ] Backtesting engine

### Phase 3
- [ ] Broker integration (Zerodha/Upstox)
- [ ] Semi-automated execution
- [ ] Telegram alerts
- [ ] Enhanced monitoring

---

## Support

For issues or questions:
1. Check logs: `logs/astra.log`
2. Review documentation: `/docs`
3. Check API docs: http://localhost:8000/docs

---

## Disclaimer

This software is for educational purposes only. Trading in financial markets involves substantial risk. Always test thoroughly in paper trading mode before considering live deployment. Past performance does not guarantee future results.
