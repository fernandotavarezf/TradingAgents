# FILE: execute_trades_vf.py
"""
Iterate over multiple tickers, allocating a fraction of cash per BUY and
fully closing positions on SELL.

Prereqs
-------
• pip install alpaca-py python-dotenv
• .env must contain ALPACA_KEY_PAPER / ALPACA_SECRET_PAPER
"""

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
import os, sys, math, time

# ---------------------------------------------------------------
# 1. Environment & constants
# ---------------------------------------------------------------
load_dotenv()
API_KEY    = os.getenv("ALPACA_KEY_PAPER")
API_SECRET = os.getenv("ALPACA_SECRET_PAPER")
if not all([API_KEY, API_SECRET]):
    sys.exit("❌  Missing ALPACA creds in .env")

FRACTION = 0.1        # ⬅︎ 0.2 % of *current* cash per BUY
TIME_IN_FORCE = TimeInForce.DAY
# Replace this dict with calls to TradingAgentsGraph later
decisions = {
    "NVDA": "SELL",
    "AAPL": "BUY",
    "MSFT": "HOLD"
}

# ---------------------------------------------------------------
# 2. Clients
# ---------------------------------------------------------------
trade_client = TradingClient(API_KEY, API_SECRET, paper=True)
data_client  = StockHistoricalDataClient(API_KEY, API_SECRET)

# ---------------------------------------------------------------
# 3. Helper utilities
# ---------------------------------------------------------------
def cash_balance() -> float:
    return float(trade_client.get_account().cash)

def latest_prices(symbols):
    """
    Return {symbol: price, ...} for a list/tuple of symbols.
    One API hit for all of them.
    """
    req  = StockLatestTradeRequest(symbol_or_symbols=list(symbols))
    resp = data_client.get_stock_latest_trade(req)   # dict(symbol -> Trade)
    return {sym: float(resp[sym].price) for sym in symbols}

def floor_qty(dollars, price):
    return max(math.floor(dollars / price), 1)

# ---------------------------------------------------------------
# 4. Trade loop
# ---------------------------------------------------------------
print(f"💰  Starting cash: ${cash_balance():,.2f}\n")

buy_symbols   = [s for s, d in decisions.items() if d.upper() == "BUY"]
sell_symbols  = [s for s, d in decisions.items() if d.upper() == "SELL"]

# Batch-fetch prices only for BUY symbols
price_map = latest_prices(buy_symbols) if buy_symbols else {}

for symbol, decision in decisions.items():
    decision = decision.upper()

    if decision == "BUY":
        price = price_map[symbol]
        dollars_out = cash_balance() * FRACTION      # update cash just-in-time
        qty = floor_qty(dollars_out, price)

        order = MarketOrderRequest(
            symbol=symbol, qty=qty, side=OrderSide.BUY,
            time_in_force=TIME_IN_FORCE
        )
        trade_client.submit_order(order)
        print(f"✅  BUY  {symbol:<5} | {qty} @ ≈ ${price:.2f} "
              f"(≈ ${qty*price:,.2f})  Remaining cash: ${cash_balance():,.2f}")

    elif decision == "SELL":
        try:
            qty = int(trade_client.get_open_position(symbol).qty)
        except Exception:
            print(f"ℹ️  SELL {symbol:<5} | No open position → skipped.")
            continue

        order = MarketOrderRequest(
            symbol=symbol, qty=qty, side=OrderSide.SELL,
            time_in_force=TIME_IN_FORCE
        )
        trade_client.submit_order(order)
        print(f"✅  SELL {symbol:<5} | {qty} shares closed  "
              f"New cash: ${cash_balance():,.2f}")

    else:  # HOLD or anything else
        print(f"⏸  HOLD {symbol:<5} | No action taken.")

    # Tiny pause so you can read logs in real time (optional)
    time.sleep(0.25)

print(f"\n🏁  Finished. Ending cash: ${cash_balance():,.2f}")