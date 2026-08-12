import requests
import streamlit as st
from config import FXMACRO_KEY

BASE_URL = "https://api.fxmacrodata.com/v1"

CURRENCY_MAP = {
    "USD": "usd", "EUR": "eur", "GBP": "gbp", "JPY": "jpy",
    "CHF": "chf", "AUD": "aud", "CAD": "cad", "NZD": "nzd",
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

def get_real_interest_rate(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return None, None, None
    rate_data = _fetch(code, "policy_rate")
    cpi_data  = _fetch(code, "inflation")
    if not rate_data or not cpi_data:
        return None, None, None
    nominal = rate_data[0]["val"]
    cpi     = cpi_data[0]["val"]
    real    = nominal - cpi
    return real, nominal, cpi

def get_macro_score(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return 0, {}
    score = 0
    details = {}

    # Real Interest Rate
    real_rate, nominal, cpi = get_real_interest_rate(currency)
    if real_rate is not None:
        if real_rate > 2:
            score += 35
            details["Real Rate"] = f"+35 (High: {real_rate:.2f}%)"
        elif real_rate > 0:
            score += 20
            details["Real Rate"] = f"+20 (Positive: {real_rate:.2f}%)"
        elif real_rate > -1:
            score -= 10
            details["Real Rate"] = f"-10 (Slightly Negative: {real_rate:.2f}%)"
        else:
            score -= 30
            details["Real Rate"] = f"-30 (Very Negative: {real_rate:.2f}%)"

    # Current Account / Trade Balance
    trade_data = _fetch(code, "trade_balance")
    if len(trade_data) >= 2:
        if trade_data[0]["val"] > 0 and trade_data[0]["val"] > trade_data[1]["val"]:
            score += 25
            details["Trade Balance"] = f"+25 (Surplus & Improving)"
        elif trade_data[0]["val"] > 0:
            score += 15
            details["Trade Balance"] = f"+15 (Surplus)"
        elif trade_data[0]["val"] < 0 and trade_data[0]["val"] < trade_data[1]["val"]:
            score -= 25
            details["Trade Balance"] = f"-25 (Deficit & Worsening)"
        else:
            score -= 10
            details["Trade Balance"] = f"-10 (Deficit)"

    # Carry
    if nominal is not None:
        if nominal > 4:
            score += 20
            details["Carry"] = f"+20 (Very Attractive: {nominal:.2f}%)"
        elif nominal > 2:
            score += 10
            details["Carry"] = f"+10 (Attractive: {nominal:.2f}%)"
        elif nominal < 0.5:
            score -= 20
            details["Carry"] = f"-20 (Unattractive: {nominal:.2f}%)"

    return score, details

def get_hawkish_dovish_ranking():
    from cb_bias_auto import get_cb_bias_auto
    from config import CURRENCIES
    ranking = []
    for c in CURRENCIES:
        bias = get_cb_bias_auto(c)
        ranking.append({
            "currency": c,
            "rate": bias["rate"],
            "bias": bias["bias"],
            "trend": bias["trend"],
            "last_change": bias["last_change"],
            "score": bias["score"],
        })
    return sorted(ranking, key=lambda x: x["score"], reverse=True)

def get_all_differentials():
    from config import CURRENCIES
    ranking = get_hawkish_dovish_ranking()
    rates = {r["currency"]: r["rate"] for r in ranking}
    diffs = []
    currencies = list(rates.keys())
    for i in range(len(currencies)):
        for j in range(i+1, len(currencies)):
            c1, c2 = currencies[i], currencies[j]
            diff = abs(rates[c1] - rates[c2])
            favor = c1 if rates[c1] > rates[c2] else c2
            attract = "🟢 High" if diff > 2 else "🟡 Moderate" if diff > 1 else "⚪ Low"
            diffs.append({
                "Pair": f"{c1}/{c2}",
                "Rate 1": f"{rates[c1]:.2f}%",
                "Rate 2": f"{rates[c2]:.2f}%",
                "Differential": f"{diff:.2f}%",
                "Favor": favor,
                "Attractiveness": attract,
            })
    return sorted(diffs, key=lambda x: float(x["Differential"].replace("%","")), reverse=True)
