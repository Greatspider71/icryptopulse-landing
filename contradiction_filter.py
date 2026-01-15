# contradiction_filter.py

import csv
from datetime import datetime, timedelta

SIGNAL_LOG = "signals_log.csv"
TIME_WINDOW_MINUTES = 60  # How far back to look for conflicting signals

def has_contradiction(asset, current_signal, now_utc=None):
    if not now_utc:
        now_utc = datetime.utcnow()

    signals = []

    try:
        with open(SIGNAL_LOG, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Asset"] != asset or not row["Timestamp"]:
                    continue

                try:
                    ts = datetime.strptime(row["Timestamp"], "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if now_utc - ts <= timedelta(minutes=TIME_WINDOW_MINUTES):
                    signals.append(row["Signal"].upper())
    except:
        return False  # If log is missing, allow through

    signal_set = set(signals + [current_signal.upper()])
    if len(signal_set) > 1:
        return True  # Conflict exists

    return False