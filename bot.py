import ccxt
import pandas as pd
import requests
import os
import json
from datetime import datetime, timezone

# ===============================
# 🤖 BOT SOURCE
# ===============================
BOT_SOURCE = "GitHub Actions"

# ===============================
# 🔐 TELEGRAM (SECURE)
# ===============================
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "-1003734649641"

# ===============================
# ⚙️ SETTINGS
# ===============================
PAIRS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
TIMEFRAMES = ["15m", "30m", "1h", "4h"]

EMA_FAST = 20
EMA_SLOW = 50
MIN_CANDLES = 150

STATE_FILE = "last_signal.json"

# ===============================
# 🔁 EXCHANGE
# ===============================
exchange = ccxt.mexc({
    "enableRateLimit": True
})

# ===============================
# 📂 LOAD STATE
# ===============================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# ===============================
# 📩 TELEGRAM
# ===============================
def send_alert(text):
    if not TOKEN:
        print("BOT_TOKEN not found!")
        return

    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=15
        )
    except Exception as e:
        print("Telegram Error:", e)

# ===============================
# 📊 FETCH DATA
# ===============================
def get_data(symbol, timeframe):
    try:
        candles = exchange.fetch_ohlcv(symbol, timeframe, limit=200)
        df = pd.DataFrame(
            candles,
            columns=["time", "open", "high", "low", "close", "volume"]
        )
        return df
    except Exception as e:
        print("Fetch Error:", e)
        return None

# ===============================
# 🚨 CROSSOVER LOGIC
# ===============================
def check_signal(symbol, timeframe, state):

    df = get_data(symbol, timeframe)

    if df is None or len(df) < MIN_CANDLES:
        return

    df["ema_fast"] = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    df["ema_slow"] = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

    prev_fast = df["ema_fast"].iloc[-3]
    prev_slow = df["ema_slow"].iloc[-3]

    last_fast = df["ema_fast"].iloc[-2]
    last_slow = df["ema_slow"].iloc[-2]

    price = df["close"].iloc[-2]

    signal = None

    if prev_fast < prev_slow and last_fast > last_slow:
        signal = "BUY"
    elif prev_fast > prev_slow and last_fast < last_slow:
        signal = "SELL"

    if signal is None:
        return

    key = f"{symbol}_{timeframe}"
    last_saved_signal = state.get(key)

    if last_saved_signal == signal:
        return

    now = datetime.now(timezone.utc)

    message = (
        f"{'🟢 BUY EMA CROSS' if signal=='BUY' else '🔴 SELL EMA CROSS'}\n\n"
        f"🤖 Source: {BOT_SOURCE}\n\n"
        f"📊 Pair: {symbol}\n"
        f"⏱ Timeframe: {timeframe}\n"
        f"💰 Price: {price}\n"
        f"🕒 UTC: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    send_alert(message)

    state[key] = signal
    print(f"Signal sent: {symbol} {timeframe} {signal}")

# ===============================
# ▶️ MAIN
# ===============================
def main():

    state = load_state()

    # ✅ Bot start message ONLY when manual run
    if os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch":
        send_alert(
            "✅ Crypto EMA Cross Bot Started\n\n"
            f"🤖 Source: {BOT_SOURCE}\n"
            "📊 Strategy: EMA 20 / 50 Crossover\n"
            "⏱ Timeframes: 15m, 30m, 1h, 4h\n"
            f"🕒 UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )

    for pair in PAIRS:
        for tf in TIMEFRAMES:
            check_signal(pair, tf, state)

    save_state(state)

if __name__ == "__main__":
    main()
    
