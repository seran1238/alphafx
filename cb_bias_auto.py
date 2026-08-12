import requests
import streamlit as st
from config import FXMACRO_KEY

BASE_URL = "https://api.fxmacrodata.com/v1"

CURRENCY_MAP = {
    "USD": "usd", "EUR": "eur", "GBP": "gbp", "JPY": "jpy",
    "CHF": "chf", "AUD": "aud", "CAD": "cad", "NZD": "nzd",
}

@st.cache_data(ttl=86400)
def get_cb_bias_auto(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return {"bias": "Unknown", "trend": "Unknown", "rate": 0, "last_change": "Unknown", "score": 50}

    try:
        url = f"{BASE_URL}/announcements/{code}/policy_rate?api_key={FXMACRO_KEY}&limit=8"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return {"bias": "Unknown", "trend": "Unknown", "rate": 0, "last_change": "Unknown", "score": 50}

        data = r.json().get("data", [])
        if not data:
            return {"bias": "Unknown", "trend": "Unknown", "rate": 0, "last_change": "Unknown", "score": 50}

        latest = data[0]
        current_rate = latest.get("val", 0)
        change_bps = latest.get("target_range_change_bps", latest.get("change_from_previous", 0))

        # Trend: letzte Entscheidung + Richtung der letzten 3
        # Summiere alle Änderungen der letzten 8 Entscheidungen
        all_changes = [d.get("change_from_previous", 0) for d in data]
        total_6m = sum(all_changes[:6])
        last = all_changes[0]
        cuts = sum(1 for c in all_changes[:6] if c < 0)
        hikes = sum(1 for c in all_changes[:6] if c > 0)

        if total_6m < -0.1 or cuts > hikes:
            trend = "Cutting"
            bias = "Dovish"
            last_change = f"{total_6m:+.2f}% (6M)"
        elif total_6m > 0.1 or hikes > cuts:
            trend = "Hiking"
            bias = "Hawkish"
            last_change = f"{total_6m:+.2f}% (6M)"
        else:
            trend = "Hold"
            bias = "Neutral"
            last_change = "Hold"
        total_change = total_6m

        # Score: höherer Zins + Hiking = stärker
        score = 50 + (current_rate * 3) + (total_change * 10)
        score = max(0, min(100, score))

        return {
            "bias": bias,
            "trend": trend,
            "rate": round(current_rate, 3),
            "last_change": last_change,
            "score": round(score, 1),
        }

    except Exception as e:
        return {"bias": "Unknown", "trend": "Unknown", "rate": 0, "last_change": f"Error: {e}", "score": 50}
