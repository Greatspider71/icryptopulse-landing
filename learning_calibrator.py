# learning_calibrator.py

import csv
import os
import json
from collections import defaultdict

SIGNAL_LOG = "signals_log.csv"
CALIBRATION_FILE = "calibration.json"
MAX_SIGNALS = 100  # how many most recent completed signals to learn from

def load_recent_signals():
    if not os.path.exists(SIGNAL_LOG):
        print("❌ signals_log.csv not found.")
        return []

    signals = []

    with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                change = float(row.get("Price_Change_%", ""))
                conf = int(float(row["Confidence"]))
                source = row.get("Source", "symbol_map")
                ticker_source = row.get("Asset", "unknown")
                news_id = row["URL"]

                signals.append({
                    "confidence": conf,
                    "ticker_source": "gpt" if "gpt" in news_id.lower() else "symbol_map",
                    "price_change": change,
                    "news_id": news_id,
                })
            except:
                continue

    # Only keep latest N signals with outcome
    return list(reversed(signals))[:MAX_SIGNALS]

def analyze_performance(signals):
    groups = {"gpt": [], "symbol_map": []}

    for s in signals:
        if s["ticker_source"] not in groups:
            continue
        groups[s["ticker_source"]].append(s)

    stats = {}

    for group, entries in groups.items():
        count = len(entries)
        if count == 0:
            continue

        wins = sum(1 for e in entries if e["price_change"] > 0)
        avg_move = sum(e["price_change"] for e in entries) / count
        win_rate = 100 * wins / count

        stats[group] = {
            "count": count,
            "win_rate": win_rate,
            "avg_move": avg_move,
        }

    return stats

def suggest_penalties(performance_stats):
    # Default base penalties
    default = {
        "gpt_ticker_penalty": 15,
        "single_source_penalty": 10,
        "no_move_penalty": 20
    }

    if "gpt" not in performance_stats:
        return default

    gpt_accuracy = performance_stats["gpt"]["win_rate"]

    # Adjust GPT penalty
    if gpt_accuracy >= 70:
        penalty = 5
    elif gpt_accuracy >= 60:
        penalty = 10
    elif gpt_accuracy >= 50:
        penalty = 15
    else:
        penalty = 20

    return {
        "gpt_ticker_penalty": penalty,
        "single_source_penalty": default["single_source_penalty"],  # static for now
        "no_move_penalty": default["no_move_penalty"]
    }

def save_calibration(penalties):
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as f:
        json.dump(penalties, f, indent=2)
    print(f"✅ Saved updated penalties to {CALIBRATION_FILE}:", penalties)

def main():
    signals = load_recent_signals()
    if not signals:
        print("⚠️ No signals with outcomes found.")
        return

    stats = analyze_performance(signals)
    print("\n📊 Signal Accuracy Analysis:")
    for group, data in stats.items():
        print(f" - {group.upper()}: {data['win_rate']:.1f}% win rate over {data['count']} signals")

    penalties = suggest_penalties(stats)
    save_calibration(penalties)

if __name__ == "__main__":
    main()