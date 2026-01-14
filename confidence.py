# confidence.py

import json
import os

# === Default Penalties (used if calibration.json is missing) ===
DEFAULT_PENALTIES = {
    "gpt_ticker_penalty": 15,
    "single_source_penalty": 10,
    "no_move_penalty": 20
}

CALIBRATION_FILE = "calibration.json"

def load_penalties():
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            print("⚠️ Failed to read calibration.json — using default penalties.")
    return DEFAULT_PENALTIES


def calibrate_confidence(
    raw_confidence: int,
    ticker_source: str,
    source_count: int,
    historical_price_change: float | None
) -> int:
    """
    Adjust GPT confidence based on reliability heuristics.

    Parameters:
    - raw_confidence: GPT confidence (0–100)
    - ticker_source: 'symbol_map' or 'gpt'
    - source_count: number of RSS feeds mentioning this news
    - historical_price_change: % price change after 3h (None if unknown)

    Returns:
    - calibrated confidence (int)
    """

    penalties = load_penalties()
    confidence = raw_confidence

    # 1️⃣ Penalty if GPT guessed the ticker
    if ticker_source == "gpt":
        confidence -= penalties.get("gpt_ticker_penalty", 15)

    # 2️⃣ Penalty if single-source news
    if source_count <= 1:
        confidence -= penalties.get("single_source_penalty", 10)

    # 3️⃣ Penalty if historical reaction weak or wrong
    if historical_price_change is not None:
        if abs(historical_price_change) < 0.3:
            confidence -= penalties.get("no_move_penalty", 20)
        elif historical_price_change < 0:
            confidence -= penalties.get("no_move_penalty", 20)

    # 4️⃣ Clamp confidence
    confidence = max(35, min(100, confidence))

    return int(confidence)