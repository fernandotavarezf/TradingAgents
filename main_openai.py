"""Example script for running TradingAgents on multiple tickers."""

from datetime import date
from dotenv import load_dotenv

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


load_dotenv()  # Load environment variables from .env

# Configure the TradingAgents graph
config = DEFAULT_CONFIG.copy()
config["online_tools"] = True
ta = TradingAgentsGraph(debug=True, config=config)

# Tickers to analyze
tickers = ["AMZN"]

# Use today's date for the trade analysis
today = date.today().isoformat()

# Collect the decisions for each ticker
decisions = {}
for ticker in tickers:
    _, decision = ta.propagate(ticker, today)
    decisions[ticker] = decision

print(decisions)
