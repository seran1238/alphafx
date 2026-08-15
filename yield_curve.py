import requests
import time
import streamlit as st
from config import FXMACRO_KEY

BASE_URL = "https://api.fxmacrodata.com/v1"

CURRENCY_MAP = {
    "USD": "usd", "EUR": "eur", "GBP": "gbp", "JPY": "jpy",
    "CHF": "chf", "AUD": "aud", "CAD": "cad", "NZD": "nzd",
}

@st.cache_data(ttl=86400)
def _fetch_yield(code, indicator):
    for attempt in range(3):
        try:
            url = f"{BASE_URL}/announcements/{code}/{indicator}?api_key={FXMACRO_KEY}&limit=3"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    return [d["val"] for d in data]
        except Exception:
            time.sleep(1)
    return []

def get_yield_curve_score(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return 0, {}

    score = 0
    details = {}

    y2_data  = _fetch_yield(code, "gov_bond_2y")
    y10_data = _fetch_yield(code, "gov_bond_10y")

    # Fallback: nutze Policy Rate als 2y Proxy
    if not y2_data:
        try:
            from cb_bias_auto import get_cb_bias_auto
            cb = get_cb_bias_auto(currency)
            y2 = cb["rate"]
        except:
            y2 = None
    else:
        y2 = y2_data[0]

    y10 = y10_data[0] if y10_data else None

    if y10 is not None and y2 is not None:
        spread = y10 - y2

        if spread > 1.0:
            score += 25
            details["Yield Curve"] = f"✅ Steil +{spread:.2f}% — Starkes Wachstum"
        elif spread > 0.5:
            score += 20
            details["Yield Curve"] = f"✅ Normal +{spread:.2f}% — Wachstum erwartet"
        elif spread > 0:
            score += 10
            details["Yield Curve"] = f"🟡 Flach +{spread:.2f}% — Unsicher"
        elif spread > -0.5:
            score -= 10
            details["Yield Curve"] = f"🟠 Leicht invertiert {spread:.2f}%"
        else:
            score -= 25
            details["Yield Curve"] = f"🔴 Invertiert {spread:.2f}% — Rezessionsrisiko"

        # Trend
        if len(y10_data) >= 2:
            prev_spread = y10_data[1] - y2
            if spread > prev_spread + 0.05:
                score += 5
                details["YC Trend"] = "📈 Steepening"
            elif spread < prev_spread - 0.05:
                score -= 5
                details["YC Trend"] = "📉 Flattening"
            else:
                details["YC Trend"] = "➡️ Stable"

        details["2y"] = f"{y2:.2f}%"
        details["10y"] = f"{y10:.2f}%"

    elif y10:
        details["Yield Curve"] = f"10y: {y10:.2f}% (kein 2y)"
    else:
        details["Yield Curve"] = "N/A"

    return score, details


def get_all_yield_curves():
    from config import CURRENCIES
    results = []
    for c in CURRENCIES:
        score, details = get_yield_curve_score(c)
        results.append({
            "currency": c,
            "score": score,
            "details": details,
            "yield_curve": details.get("Yield Curve", "N/A"),
            "trend": details.get("YC Trend", "N/A"),
        })
    return results
