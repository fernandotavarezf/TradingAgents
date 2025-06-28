"""Generate daily Markdown reports using TradingAgents.

Example:
    python scripts/generate_daily_reports.py AAPL NVDA MSFT
"""

from __future__ import annotations

import datetime
import pprint
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

DEFAULT_TICKERS = ["AAPL"]


def create_report_content(ticker: str, date_str: str, decision: str, analysis: object) -> str:
    """Return the Markdown report for a ticker."""
    analysis_repr = pprint.pformat(analysis, indent=2)
    lines = [
        f"# {ticker} — {date_str}",
        f"Decision: {decision}",
        "",
        "Analysis",
        analysis_repr,
        "",
    ]
    return "\n".join(lines)


def generate_reports(tickers: Iterable[str], date: str) -> None:
    """Run TradingAgents and write reports for each ticker."""
    load_dotenv()
    config = DEFAULT_CONFIG.copy()
    config["online_tools"] = True
    ta = TradingAgentsGraph(debug=True, config=config)

    output_dir = Path("reports") / date
    output_dir.mkdir(parents=True, exist_ok=True)

    for ticker in tickers:
        try:
            analysis, decision = ta.propagate(ticker, date)
            content = create_report_content(ticker, date, decision, analysis)
            (output_dir / f"{ticker}_{date}.md").write_text(content)
        except Exception as exc:  # noqa: BLE001
            print(f"Error processing {ticker}: {exc}", file=sys.stderr)


def main() -> None:
    """Entry point for command-line execution."""
    tickers = sys.argv[1:] or DEFAULT_TICKERS
    today = datetime.date.today().isoformat()
    generate_reports(tickers, today)


if __name__ == "__main__":
    main()