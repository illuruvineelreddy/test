# Upstox Integration Guide

## ✅ Credentials Configured

Your Upstox API credentials have been successfully integrated into Project Astra.

### Configuration Files Updated

1. **`.env`** - Contains your actual credentials (⚠️ NEVER commit this file)
2. **`.env.example`** - Template for other developers
3. **`configs/settings.py`** - Updated with Upstox-specific settings
4. **`app/market_data/broker_client.py`** - New Upstox client implementation

---

## 🔑 Your Current Configuration

```
API Key: 24e0bc8e-****-****-****-********9b9d
Environment: live
Trading Mode: paper (safe for testing)
```

---

## 📦 Installation

Install the Upstox Python SDK:

```bash
pip install upstox-api
```

Add to requirements.txt:
```
upstox-api>=2.1.0
```

---

## 🚀 Usage

### Initialize Client

```python
from app.market_data.broker_client import get_upstox_client

client = get_upstox_client()

# Initialize connection
if client.initialize():
    print("Connected to Upstox!")
else:
    print("Running in mock mode")
```

### Get Real-Time Quotes

```python
# Subscribe to instruments
instruments = [
    client.get_instrument_key('NIFTY'),
    client.get_instrument_key('BANKNIFTY'),
    client.get_instrument_key('RELIANCE'),
]

client.subscribe(instruments)

# Get quotes
quotes = client.get_quotes(instruments)
print(quotes)
```

### Place Orders

```python
# Place a limit order
order = client.place_order(
    symbol='NIFTY',
    transaction_type='BUY',
    product_type='INTRADAY',  # DELIVERY, INTRADAY, MARGIN, COVERAGE
    order_type='LIMIT',       # MARKET, LIMIT, SL, SL-M
    quantity=50,
    price=22000.0,
    validity='DAY'
)

print(f"Order ID: {order['order_id']}")
```

### Modify/Cancel Orders

```python
# Modify order
client.modify_order(
    order_id='YOUR_ORDER_ID',
    price=22100.0
)

# Cancel order
client.cancel_order(order_id='YOUR_ORDER_ID')
```

### Get Positions & Orders

```python
# Get all positions
positions = client.get_positions()

# Get all holdings
holdings = client.get_holdings()

# Get today's orders
orders = client.get_orders()
```

---

## 🛡️ Safety Features

### Paper Trading Mode

Currently set to `TRADING_MODE=paper` in `.env`:

- All orders are simulated (mocked)
- No real money is used
- Perfect for testing strategies

### To Enable Live Trading

⚠️ **WARNING**: Only do this after thorough testing!

1. Complete 3-6 months of paper trading
2. Verify strategy performance
3. Change in `.env`:
   ```
   TRADING_MODE=semi_auto  # Requires human approval
   ```
4. Restart the application

---

## 📊 Instrument Mapping

| Symbol | Upstox Instrument Key |
|--------|----------------------|
| NIFTY | `NSE_INDEX\|Nifty` |
| BANKNIFTY | `NSE_INDEX\|Bank Nifty` |
| FINNIFTY | `NSE_INDEX\|Fin Nifty` |
| RELIANCE | `NSE_EQ\|INE002A01018` |
| TCS | `NSE_EQ\|INE467B01029` |

For F&O instruments, use Upstox's instrument master file to get the correct token.

---

## 🔒 Security Best Practices

1. **Never commit `.env` to Git** (already in `.gitignore`)
2. **Rotate credentials regularly**
3. **Use environment variables in production**
4. **Enable IP whitelisting in Upstox dashboard**
5. **Monitor API usage and set rate limits**

---

## 🐛 Troubleshooting

### "Upstox SDK not installed"
```bash
pip install upstox-api
```

### "Invalid access token"
- Tokens expire daily
- Generate new token using Upstox OAuth flow
- Update `UPSTOX_ACCESS_TOKEN` in `.env`

### "WebSocket connection failed"
- Check internet connection
- Verify API credentials
- Ensure market hours (9:15 AM - 3:30 PM IST)

---

## 📚 Resources

- [Upstox API Documentation](https://upstox.com/api-docs/)
- [Upstox Python SDK](https://github.com/upstox/upstox-python-sdk)
- [Instrument Master File](https://assets.upstox.com/market-quote/instruments/exchange/2024-01-01.csv)

---

## ⚠️ Important Notes

1. **Access Token Expiry**: Upstox access tokens expire daily. You'll need to implement token refresh logic or generate new tokens each trading day.

2. **Market Hours**: Indian markets operate 9:15 AM - 3:30 PM IST. Orders outside these hours may be rejected.

3. **Rate Limits**: Upstox has API rate limits. The current implementation doesn't include rate limiting - add this for production.

4. **OAuth Flow**: For initial setup, you need to complete Upstox's OAuth flow to get the access token. This is a one-time manual process per day.

---

## Next Steps

1. ✅ Install Upstox SDK: `pip install upstox-api`
2. ✅ Test in paper trading mode
3. ⏳ Implement WebSocket streaming
4. ⏳ Add token refresh mechanism
5. ⏳ Connect to strategy engine
6. ⏳ Monitor and log all activities

Happy Trading! 📈
