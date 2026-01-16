# telegram_gating.py

import os
import csv
from datetime import datetime

DB_FILE = "subscriber_db.csv"

def get_subscription_status(telegram_id):
    if not os.path.exists(DB_FILE):
        return False, False, None  # Return defaults if no file yet

    with open(DB_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["telegram_id"] == str(telegram_id):
                is_paid = row["is_paid"] == "1"
                is_vip = row["is_vip"] == "1"
                expires_on = row["expires_on"]
                return is_paid, is_vip, expires_on

    return False, False, None

def load_subscribers():
    """Load subscriber database into a list of dicts"""
    with open(DB_FILE, "r") as f:
        reader = csv.DictReader(f)
        return list(reader)

def update_subscriber(telegram_id, email):
    """Update CSV to store telegram_id for matching email"""
    updated = False
    rows = []

    with open(DB_FILE, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)

    for i, row in enumerate(rows):
        if i == 0:
            continue
        if row[1].strip().lower() == email.strip().lower():
            rows[i][0] = str(telegram_id)         # telegram_id
            rows[i][1] = email.strip().lower()    # email
            updated = True
            break

    if updated:
        with open(DB_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        return True
    else:
        return False

def get_subscription_status(telegram_id):
    """Returns whether user is paid or VIP and expiry date"""
    with open(DB_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["telegram_id"] == str(telegram_id):
                is_paid = row["is_paid"] == "1"
                is_vip = row["is_vip"] == "1"
                expires_on = row["expires_on"]
                return is_paid, is_vip, expires_on
    return False, False, None

def handle_register_command(telegram_id, email):
    """Main handler for /register <email> command"""
    if update_subscriber(telegram_id, email):
        is_paid, is_vip, expires_on = get_subscription_status(telegram_id)
        if is_paid or is_vip:
            return f"✅ Registered successfully. You now have VIP access until {expires_on.split('T')[0]}"
        else:
            return "⚠️ Registered, but payment not confirmed yet. Please complete your subscription."
    else:
        return "❌ Email not found in our payment records. Please check your email or try again later."