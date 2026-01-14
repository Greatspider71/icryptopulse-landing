# subscription_server.py

import os
import csv
import stripe
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv

# ✅ LOAD .env FILE
load_dotenv()

app = Flask(__name__)

# === ENV CONFIG ===
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "http://localhost:4242")

# 🔒 SAFETY CHECK
if not STRIPE_SECRET_KEY:
    raise RuntimeError("❌ STRIPE_SECRET_KEY not found. Check .env file.")

stripe.api_key = STRIPE_SECRET_KEY

DB_FILE = "subscriber_db.csv"

# === Ensure DB CSV Exists ===
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["telegram_id", "email", "is_paid", "is_vip", "expires_on"])

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        data = request.json
        email = data["email"]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",  # for recurring billing
            line_items=[{
                "price": STRIPE_PRICE_ID,  # ✅ correct for subscriptions
                "quantity": 1,
            }],
            customer_email=email,
            success_url=YOUR_DOMAIN + "/success",
            cancel_url=YOUR_DOMAIN + "/cancel"
        )

        return jsonify({"url": session.url})

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session.get("customer_email")

        expires_on = (datetime.utcnow() + timedelta(days=30)).isoformat()

        rows = []
        updated = False

        with open(DB_FILE, "r") as f:
            rows = list(csv.reader(f))

        for i, row in enumerate(rows):
            if i == 0:
                continue
            if row[1] == email:
                rows[i][2] = "1"
                rows[i][4] = expires_on
                updated = True

        if not updated:
            rows.append(["", email, "1", "0", expires_on])

        with open(DB_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    return "", 200


if __name__ == "__main__":
    app.run(port=4242)