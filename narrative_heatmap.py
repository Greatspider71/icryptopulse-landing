# narrative_heatmap.py
# Categorize today's signals into narrative sectors (e.g., AI, Layer 1, Memes)

import csv
from datetime import datetime
from collections import defaultdict

SIGNAL_LOG = "signals_log.csv"

# Define sector mappings
SECTOR_MAP = {
    "FET": "AI",
    "RNDR": "AI",
    "AGIX": "AI",
    "OCEAN": "AI",
    "NEAR": "Layer 1",
    "AVAX": "Layer 1",
    "SOL": "Layer 1",
    "ADA": "Layer 1",
    "DOT": "Layer 1",
    "INJ": "Layer 1",
    "DOGE": "Memecoin",
    "SHIB": "Memecoin",
    "FLOKI": "Memecoin",
    "BONK": "Memecoin",
    "PEPE": "Memecoin",
    "XMR": "Privacy",
    "DASH": "Privacy",
    "DUSK": "Privacy",
    "LINK": "Oracles",
    "BAND": "Oracles",
    "ATOM": "Cosmos",
    "TIA": "Cosmos",
    "JUNO": "Cosmos",
    "UNI": "DEX",
    "SUSHI": "DEX",
    "DYDX": "DEX",
    "GMX": "DEX",
    "MATIC": "Scaling",
    "OP": "Scaling",
    "ARB": "Scaling",
    "ETH": "Ethereum",
    "BTC": "Bitcoin",
    "BNB": "BNB Chain",
}


def load_today_signals():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    signals = []
    with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Timestamp"].startswith(today):
                signals.append(row)
    return signals


def map_tokens_to_sectors(signals):
    sector_scores = defaultdict(int)
    token_counts = defaultdict(int)

    for s in signals:
        ticker = s.get("Asset", "")
        confidence = int(float(s.get("Confidence", 0)))
        base = ticker.replace("USDT", "").replace("1000", "")

        if base in SECTOR_MAP:
            sector = SECTOR_MAP[base]
            sector_scores[sector] += confidence
            token_counts[sector] += 1

    return sector_scores, token_counts


def analyze_sector_narratives():
    signals = load_today_signals()
    sector_scores, token_counts = map_tokens_to_sectors(signals)

    if not sector_scores:
        return "❄️ <b>No sector momentum detected today.</b>"

    # Normalize by average confidence
    scored = [
        (sector, sector_scores[sector] / token_counts[sector])
        for sector in sector_scores
    ]
    sorted_sectors = sorted(scored, key=lambda x: x[1], reverse=True)

    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (sector, avg_score) in enumerate(sorted_sectors[:5]):
        medal = medals[i] if i < len(medals) else "•"
        lines.append(f"{medal} {sector} — {avg_score:.1f}% avg confidence")

    return "\n".join(lines)


if __name__ == "__main__":
    print(analyze_sector_narratives())