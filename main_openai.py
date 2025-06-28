from dotenv import load_dotenv
load_dotenv()  # by default loads `.env` from the current working directory

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["online_tools"] = True
ta = TradingAgentsGraph(debug=True, config=config)

_, decision = ta.propagate("NVDA", "2025-06-25")
print(decision)