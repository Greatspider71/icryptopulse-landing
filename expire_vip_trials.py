# expire_vip_trials.py

import csv
from datetime import datetime
import os

DB_FILE = "subscriber_db.csv"
BACKUP_FILE = f"logs/subscriber_db_backup_{datetime.utcnow().strftime('%Y%m%d')}.csv"

def parse_expiry(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None

def run_expiry_check():
    if not os.path.exists(DB_FILE):
        print("❌ subscriber_db.csv not found.")
        return

    with open(DB_FILE, "r") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    updated_rows = [header]
    downgraded_count = 0

    now = datetime.utcnow()

    for row in rows[1:]:
        telegram_id, email, is_paid, is_vip, expires_on = row

        if is_vip == "1":
            updated_rows.append(row)
            continue

        expiry_dt = parse_expiry(expires_on)
        if expiry_dt and expiry_dt < now:
            if is_paid == "1":
                print(f"🔻 Downgrading {email} (ID: {telegram_id}) — expired on {expires_on}")
                is_paid = "0"
                downgraded_count += 1

        updated_rows.append([telegram_id, email, is_paid, is_vip, expires_on])

    # Backup before overwrite
    os.makedirs("logs", exist_ok=True)
    with open(BACKUP_FILE, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    with open(DB_FILE, "w", newline="") as f:
        csv.writer(f).writerows(updated_rows)

    print(f"✅ Expiry check complete. {downgraded_count} users downgraded.")

if __name__ == "__main__":
    run_expiry_check()