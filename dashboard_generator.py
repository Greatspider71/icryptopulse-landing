import csv
from datetime import datetime
import plotly.graph_objects as go
import os

SIGNALS_FILE = "signals_log.csv"
OUTPUT_FILE = "dashboard.html"

def parse_confidence(row):
    try:
        return int(row["Confidence"])
    except:
        return None

def is_correct_signal(row):
    try:
        signal = row["Signal"].upper()
        price_change = float(row["Price_Change_%"])

        if signal == "BUY" and price_change > 0:
            return True
        elif signal == "SELL" and price_change < 0:
            return True
        elif signal == "HOLD":
            return None  # Neutral
        return False
    except:
        return None

def generate_dashboard():
    if not os.path.exists(SIGNALS_FILE):
        print("❌ No signals_log.csv file found.")
        return

    with open(SIGNALS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("❌ No data in signals_log.csv.")
        return

    confidences = []
    correct = 0
    total = 0
    per_day_accuracy = {}

    for row in rows:
        conf = parse_confidence(row)
        result = is_correct_signal(row)
        timestamp = row["Timestamp"][:10]  # YYYY-MM-DD

        if conf is not None:
            confidences.append(conf)

        if result is True:
            correct += 1
            total += 1
        elif result is False:
            total += 1

        if result is not None:
            if timestamp not in per_day_accuracy:
                per_day_accuracy[timestamp] = {"correct": 0, "total": 0}
            per_day_accuracy[timestamp]["total"] += 1
            if result:
                per_day_accuracy[timestamp]["correct"] += 1

    accuracy = (correct / total) * 100 if total else 0

    # === Plot accuracy over time ===
    dates = list(per_day_accuracy.keys())
    dates.sort()
    acc_vals = [
        round((per_day_accuracy[d]["correct"] / per_day_accuracy[d]["total"]) * 100, 1)
        for d in dates
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=acc_vals, mode='lines+markers', name='Accuracy %'))
    fig.update_layout(title="Daily Signal Accuracy", xaxis_title="Date", yaxis_title="Accuracy (%)")

    # === Histogram of confidence levels ===
    hist_fig = go.Figure()
    hist_fig.add_trace(go.Histogram(x=confidences, nbinsx=20))
    hist_fig.update_layout(title="Confidence Score Distribution", xaxis_title="Confidence %", yaxis_title="Frequency")

    # === Save to HTML ===
    with open(OUTPUT_FILE, "w", encoding='utf-8') as f:
        f.write("<html><head><title>iCryptoPulse Dashboard</title></head><body>")
        f.write(f"<h2>Overall Accuracy: {accuracy:.2f}%</h2>")
        f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write("<hr>")
        f.write(hist_fig.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write("</body></html>")

    print(f"✅ Dashboard saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_dashboard()