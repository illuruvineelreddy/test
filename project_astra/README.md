# Project Astra - AI Trading Platform for Indian Markets

Production-grade AI-assisted trading infrastructure for NSE/BSE/NFO markets.

## Architecture

Real-time WebSocket-based system with:
- Market data ingestion
- Feature engineering
- Regime detection
- Rule-based + ML-assisted strategies
- Risk management
- Paper trading → Semi-automation → Full automation

## Tech Stack

- **Backend**: Python 3.12, FastAPI, AsyncIO, Celery
- **Streaming**: Redis Streams, Redis Pub/Sub
- **Database**: PostgreSQL, TimescaleDB, Redis Cache
- **ML**: XGBoost, LightGBM, Scikit-learn, SHAP, MLflow
- **Frontend**: Next.js, TradingView Lightweight Charts
- **Infrastructure**: Docker Compose, AWS EC2 Mumbai, Nginx

## Directory Structure

```
project_astra/
├── app/
│   ├── api/              # REST API endpoints
│   ├── websocket/        # WebSocket handlers
│   ├── market_data/      # Tick ingestion, candle building
│   ├── feature_engine/   # Technical indicators, options features
│   ├── regime_engine/    # Market state detection
│   ├── strategies/       # Trading strategies
│   ├── ml_engine/        # ML models, confidence scoring
│   ├── risk_engine/      # Position sizing, kill switches
│   ├── execution_engine/ # Order management
│   ├── reconciliation/   # Position verification
│   ├── paper_trading/    # Simulated trading
│   ├── backtesting/      # Historical testing
│   ├── monitoring/       # Health checks, alerts
│   ├── notifications/    # Telegram, email alerts
│   ├── dashboard/        # UI components
│   └── utils/            # Helper functions
├── models/               # Trained ML models
├── configs/              # Configuration files
├── logs/                 # Application logs
├── notebooks/            # Jupyter notebooks
├── docker/               # Docker configurations
└── tests/                # Test suites
```

## Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Redis
- PostgreSQL with TimescaleDB
- Broker API credentials (Zerodha/Upstox/Fyers/Angel One/Dhan)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd project_astra

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start infrastructure
docker-compose up -d

# Run application
python -m app.main
```

## Phased Rollout

### Phase 0: Infrastructure (1-2 months)
- WebSocket connectivity
- Candle builder
- Database setup
- Basic dashboard

### Phase 1: Rule-based Paper Trading (2-3 months)
- Strategy implementation
- Risk engine
- Paper trading mode
- Reconciliation

### Phase 2: ML Integration (2 months)
- XGBoost models
- Regime detection
- SHAP explainability
- Walk-forward testing

### Phase 3: Semi-automated Live (₹1-5 lakh capital)
- Real broker execution
- Human approval workflow
- Monitoring & alerts

### Phase 4: Controlled Automation
- Auto execution
- Multi-broker failover
- Drift detection

## Core Strategies

1. **EMA Trend Following** - Long/short based on EMA crossovers
2. **VWAP Mean Reversion** - Fade extreme deviations from VWAP
3. **Momentum Breakout** - Trade volume-backed breakouts
4. **Short Straddle** - Options selling in sideways markets

## Risk Management

- Max 1% risk per trade
- Daily loss limit: 3%
- Max consecutive losses: 5
- Kill switch on anomalies
- Real-time reconciliation

## Important Notes

⚠️ **This is NOT a simple trading bot**

This system requires:
- Distributed systems engineering
- Quantitative finance knowledge
- ML engineering expertise
- Real-time infrastructure management
- Strict risk discipline

**Start with paper trading for 3-6 months minimum.**

## License

Proprietary - All rights reserved

## Disclaimer

Trading in financial markets involves substantial risk of loss. This software is for educational purposes only. Past performance does not guarantee future results. Always consult with a qualified financial advisor before making investment decisions.
