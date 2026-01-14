# event_scraper.py

import json
from datetime import datetime, timedelta

EVENTS_FILE = "weekly_events.json"

def get_mock_event_data():
    today = datetime.utcnow().date()
    day_of_week = today.weekday()  # 0 = Monday
    monday = today - timedelta(days=day_of_week)

    events = [
        {
            "day": "Wednesday",
            "date": (monday + timedelta(days=2)).isoformat(),
            "type": "Macro",
            "event": "FOMC Minutes"
        },
        {
            "day": "Thursday",
            "date": (monday + timedelta(days=3)).isoformat(),
            "type": "Unlock",
            "event": "SUI token unlock (50M)"
        },
        {
            "day": "Friday",
            "date": (monday + timedelta(days=4)).isoformat(),
            "type": "Upgrade",
            "event": "Ethereum Dencun testnet upgrade"
        }
    ]

    return events

def save_weekly_events(events):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    print(f"✅ Saved {len(events)} events to {EVENTS_FILE}")

def main():
    print("📅 Generating weekly event mockup...")
    events = get_mock_event_data()
    save_weekly_events(events)

if __name__ == "__main__":
    main()