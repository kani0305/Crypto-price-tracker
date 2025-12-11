import requests
import csv
from datetime import datetime
import time

API_URL = "https://api.coingecko.com/api/v3/simple/price"
COINS = ["bitcoin", "ethereum", "ripple", "solana", "cardano",
         "dogecoin", "tron", "litecoin", "polkadot", "binancecoin"]

PARAMS = {
    "ids": ",".join(COINS),
    "vs_currencies": "usd"
}

CSV_FILE = "crypto_prices.csv"

# ---------------------------
# SAFE API CALL
# ---------------------------
def fetch_prices():
    try:
        response = requests.get(API_URL, params=PARAMS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("⚠ API Error:", e)
        return None


# ---------------------------
# APPEND TO CSV
# ---------------------------
def append_row():
    data = fetch_prices()
    if data is None:
        print("⚠ Skipping this cycle due to API error.")
        return

    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]

    for coin in COINS:
        row.append(data.get(coin, {}).get("usd", None))

    # Write header if file empty
    try:
        with open(CSV_FILE, "x", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp"] + COINS)
    except FileExistsError:
        pass

    # Append row
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    print("Logged new prices.")


# ---------------------------
# MAIN LOOP
# ---------------------------
if __name__ == "__main__":
    while True:
        append_row()
        time.sleep(60)
