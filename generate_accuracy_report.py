# generate_accuracy_report.py

import csv
from datetime import datetime
from collections import defaultdict

SIGNAL_LOG = "signals_log.csv"
REPORT_FILE = "daily_accuracy_report.txt"


def parse_signals():
    if not SIGNAL_LOG or not os.path.exists(SIGNAL_LOG):
        print("❌ signals_log.csv not found.")
        return []

    signals = []

    with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                signal_type = row["Signal"].upper()
                confidence = int(float(row["Confidence"]))
                pct_change = float(row.get("Price_Change_%", ""))
                date = row["Timestamp"][:10]
                if not row["Price_Change_%"]:
                    continue  # Skip if no outcome yet

                signals.append({
                    "date": date,
                    "type": signal_type,
                    "confidence": confidence,
                    "result": pct_change,
                })
            except:
                continue

    return signals


def generate_report(signals):
    if not signals:
        return "No signals with price outcome found."

    today = datetime.utcnow().strftime("%Y-%m-%d")

    by_type = defaultdict(list)
    by_bucket = defaultdict(list)

    for s in signals:
        if s["date"] != today:
            continue

        by_type[s["type"]].append(s)
        bucket = (s["confidence"] // 10) * 10  # e.g., 83 → 80
        by_bucket[bucket].append(s)

    lines = [f"📊 DAILY SIGNAL REPORT ({today})\n"]

    total = sum(len(lst) for lst in by_type.values())
    lines.append(f"Total Signals Processed: {total}\n")

    for stype, lst in by_type.items():
        count = len(lst)
        wins = sum(1 for s in lst if s["result"] > 0)
        avg_move = sum(s["result"] for s in lst) / count if count else 0
        win_rate = 100 * wins / count if count else 0

        lines.append(f"🔹 {stype}: {count} signals | {win_rate:.1f}% win rate | Avg move: {avg_move:.2f}%")

    lines.append("\n🔸 Confidence Buckets:")
    for b in sorted(by_bucket.keys(), reverse=True):
        lst = by_bucket[b]
        count = len(lst)
        wins = sum(1 for s in lst if s["result"] > 0)
        win_rate = 100 * wins / count if count else 0
        lines.append(f"   {b}-{b+9}% → {count} signals | {win_rate:.1f}% win rate")

    return "\n".join(lines)


def main():
    signals = parse_signals()
    report = generate_report(signals)

    print(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
        print(f"\n✅ Report saved to: {REPORT_FILE}")


if __name__ == "__main__":
    import os
    main()