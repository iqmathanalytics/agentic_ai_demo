import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.tools.stock_data_provider import get_stock_bundle

cases = [
    ("AAPL", "NASDAQ", "Apple"),
    ("RELIANCE", "NSE", "Reliance"),
]

for sym, ex, name in cases:
    b = get_stock_bundle(sym, ex)
    if not b:
        print(f"FAIL {name}: no bundle")
        continue
    info = b["info"]
    hist = b["history"]
    print(
        f"OK {name}: source={b['source']} price={info.get('currentPrice')} "
        f"mcap={info.get('marketCap')} pe={info.get('trailingPE')} hist={len(hist)} sector={info.get('sector')}"
    )
