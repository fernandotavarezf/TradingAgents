#!/usr/bin/env python3
"""Execute trades using TradingAgents decisions and Alpaca-py.

The script queries TradingAgents for each ticker and executes BUY or SELL
orders on Alpaca. Every action is appended to ``data/trades/trade_history.csv``.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest


from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


def init_tradingagents() -> TradingAgentsGraph:
    """Initialize TradingAgents with online tools enabled."""
    config = DEFAULT_CONFIG.copy()
    config["online_tools"] = True
    return TradingAgentsGraph(debug=True, config=config)


def get_alpaca_client() -> TradingClient:
    """Create Alpaca trading client from environment variables."""
    api_key = os.getenv("ALPACA_KEY_PAPER")
    api_secret = os.getenv("ALPACA_SECRET_PAPER")
    base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    if not api_key or not api_secret:
        raise RuntimeError("Missing Alpaca credentials")
    paper = "paper" in base_url
    try:
        return TradingClient(api_key, api_secret, paper=paper, base_url=base_url)
    except TypeError:
        return TradingClient(api_key, api_secret, paper=paper)


def log_trade(row: list[str]) -> None:
    """Append a row to the trade history CSV."""
    path = Path("data/trades/trade_history.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                [
                    "timestamp",
                    "date",
                    "ticker",
                    "action",
                    "qty",
                    "notional_usd",
                    "decision",
                    "analysis_str",
                ]
            )
        writer.writerow(row)


def execute_decision(
    api: TradingClient,
    ticker: str,
    decision: str,
    analysis: dict,
    buy_pct: float,
    sell_pct: float,
    trade_date: str,
) -> None:
    """Execute a BUY or SELL decision via Alpaca and log the result."""
    timestamp = dt.datetime.utcnow().isoformat()
    analysis_str = json.dumps(analysis, ensure_ascii=False)

    if decision == "BUY":
        account = api.get_account()
        cash = float(account.cash)
        notional = cash * buy_pct
        if notional <= 0:
            return
        try:
            order_req = MarketOrderRequest(
                symbol=ticker,
                notional=notional,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            order = api.submit_order(order_req)
            qty = getattr(order, "qty", "")
            log_trade([timestamp, trade_date, ticker, "BUY", qty, notional, decision, analysis_str])
        except Exception as exc:
            print(f"Order error for {ticker}: {exc}", file=sys.stderr)
            log_trade([timestamp, trade_date, ticker, "ERROR", 0, 0, decision, str(exc)])
    elif decision == "SELL":
        try:
            position = api.get_open_position(ticker)
            qty = float(position.qty) * sell_pct
            if qty <= 0:
                return
            notional = float(position.market_value) * sell_pct
            order_req = MarketOrderRequest(
                symbol=ticker,
                qty=qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            api.submit_order(order_req)
            log_trade(
                [timestamp, trade_date, ticker, "SELL", qty, notional, decision, analysis_str]
            )
        except Exception as exc:
            print(f"Order error for {ticker}: {exc}", file=sys.stderr)
            log_trade([timestamp, trade_date, ticker, "ERROR", 0, 0, decision, str(exc)])


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Execute trades using TradingAgents")
    parser.add_argument(
        "tickers", nargs="*", default=["NU"], help="Ticker symbols"
    )
    parser.add_argument(
        "--buy-percent",
        type=float,
        default=0.10,
        dest="buy_pct",
        help="Percent of cash to spend on BUY",
    )
    parser.add_argument(
        "--sell-percent",
        type=float,
        default=1.0,
        dest="sell_pct",
        help="Percent of position to sell on SELL",
    )
    args = parser.parse_args()

    ta = init_tradingagents()
    api = get_alpaca_client()

    trade_date = dt.date.today().isoformat()

    for ticker in args.tickers:
        analysis, decision = ta.propagate(ticker, trade_date)

        decision_upper = decision.strip().upper()
        if decision_upper == "HOLD":
            continue
        execute_decision(
            api,
            ticker,
            decision_upper,
            analysis,
            args.buy_pct,
            args.sell_pct,
            trade_date,
        )


if __name__ == "__main__":
    main()