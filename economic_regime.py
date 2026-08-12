import requests
import streamlit as st
from config import FXMACRO_KEY

BASE_URL = "https://api.fxmacrodata.com/v1"

CURRENCY_MAP = {
    "USD": "usd", "EUR": "eur", "GBP": "gbp", "JPY": "jpy",
    "CHF": "chf", "AUD": "aud", "CAD": "cad", "NZD": "nzd",
}

REGIME_META = {
    (True,  False): ("Goldilocks",  "🌤️",  "Growth↑ Inflation↓ — Risk-On, EUR/GBP favoured"),
    (True,  True):  ("Reflation",   "🔥",  "Growth↑ Inflation↑ — Commodity FX (AUD/CAD/NZD)"),
    (False, True):  ("Stagflation", "⚠️",  "Growth↓ Inflation↑ — Safe Havens (USD/CHF/JPY)"),
    (False, False): ("Deflation",   "❄️",  "Growth↓ Inflation↓ — USD/JPY defensive"),
}

REGIME_BIAS = {
    "Goldilocks": {
        "USD": -10, "EUR": +20, "GBP": +15, "JPY": +5,
        "CHF":  +5, "AUD":  +5, "CAD":  0,  "NZD":  0,
    },
    "Reflation": {
        "USD": -15, "EUR": +10, "GBP": +10, "JPY": -20,
        "CHF": -10, "AUD": +25, "CAD": +25, "NZD": +20,
    },
    "Stagflation": {
        "USD": +20, "EUR": -15, "GBP": -10, "JPY": +15,
        "CHF": +20, "AUD": -20, "CAD": -10, "NZD": -20,
    },
    "Deflation": {
        "USD": +25, "EUR":  -5, "GBP": -10, "JPY": +20,
        "CHF": +20, "AUD": -25, "CAD": -20, "NZD": -25,
    },
}

@st.cache_data(ttl=86400)
def _fetch(code, indicator, limit=4):
    try:
        url = f"{BASE_URL}/announcements/{code}/{indicator}?api_key={FXMACRO_KEY}&limit={limit}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", [])
    except:
        pass
    return []

@st.cache_data(ttl=86400)
def get_regime(anchor="USD"):
    code = CURRENCY_MAP.get(anchor, "usd")

    # GDP Momentum
    gdp_data = _fetch(code, "gdp", limit=4)
    gdp_mom = None
    if len(gdp_data) >= 2:
        latest = gdp_data[0]["val"]
        prior = gdp_data[1]["val"]
        if prior != 0:
            gdp_mom = ((latest - prior) / abs(prior)) * 100

    # CPI Momentum
    cpi_data = _fetch(code, "inflation", limit=4)
    cpi_mom = None
    if len(cpi_data) >= 2:
        cpi_mom = cpi_data[0]["val"] - cpi_data[1]["val"]

    growth_rising    = gdp_mom is not None and gdp_mom > 0
    inflation_rising = cpi_mom is not None and cpi_mom > 0

    name, emoji, desc = REGIME_META[(growth_rising, inflation_rising)]

    return {
        "regime":        name,
        "emoji":         emoji,
        "description":   desc,
        "growth_mom":    round(gdp_mom, 3) if gdp_mom is not None else None,
        "inflation_mom": round(cpi_mom, 3) if cpi_mom is not None else None,
        "currency_bias": REGIME_BIAS[name],
    }

def get_regime_bias(currency):
    r = get_regime()
    score = r["currency_bias"].get(currency, 0)
    label = f"{r['emoji']} {r['regime']} → {r['description']}"
    return score, label

def get_regime_display():
    r = get_regime()
    g = f"{r['growth_mom']:+.2f}%" if r["growth_mom"] is not None else "N/A"
    i = f"{r['inflation_mom']:+.2f}%" if r["inflation_mom"] is not None else "N/A"
    return (
        f"{r['emoji']} **{r['regime']}** — {r['description']}  "
        f"| Growth: {g}  | Inflation: {i}"
    )
