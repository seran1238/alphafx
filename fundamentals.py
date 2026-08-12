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


def get_fundamental_score(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return {"score": 0, "bullish": 0, "bearish": 0, "total": 0, "details": {}}

    signals = []
    details = {}

    # 1. Policy Rate Level
    rate_data = _fetch(code, "policy_rate")
    if rate_data:
        rate = rate_data[0]["val"]
        if rate > 3:
            signals.append(1)
            details["Rate Level"] = f"✅ High ({rate:.2f}%)"
        elif rate > 1:
            signals.append(0.5)
            details["Rate Level"] = f"🟡 Moderate ({rate:.2f}%)"
        elif rate < 0.5:
            signals.append(-1)
            details["Rate Level"] = f"❌ Very Low ({rate:.2f}%)"
        else:
            signals.append(0)
            details["Rate Level"] = f"⚪ Low ({rate:.2f}%)"

    # 2. Rate Momentum (6M)
    if len(rate_data) >= 4:
        changes = [d.get("change_from_previous", 0) for d in rate_data[:6]]
        total = sum(changes)
        if total > 0.1:
            signals.append(1)
            details["Rate Momentum"] = f"✅ Hiking ({total:+.2f}%)"
        elif total < -0.1:
            signals.append(-1)
            details["Rate Momentum"] = f"❌ Cutting ({total:+.2f}%)"
        else:
            signals.append(0)
            details["Rate Momentum"] = f"⚪ Hold"

    # 3. CPI Inflation
    cpi_data = _fetch(code, "inflation")
    if len(cpi_data) >= 2:
        cpi = cpi_data[0]["val"]
        prev_cpi = cpi_data[1]["val"]
        if 1.5 <= cpi <= 3.0:
            signals.append(1)
            details["CPI"] = f"✅ On Target ({cpi:.1f}%)"
        elif cpi > 4:
            signals.append(-0.5)
            details["CPI"] = f"🟠 Too High ({cpi:.1f}%)"
        elif cpi < 0:
            signals.append(-1)
            details["CPI"] = f"❌ Deflation ({cpi:.1f}%)"
        else:
            signals.append(0)
            details["CPI"] = f"⚪ Below Target ({cpi:.1f}%)"

    # 4. CPI Momentum
    if len(cpi_data) >= 2:
        cpi_mom = cpi_data[0]["val"] - cpi_data[1]["val"]
        if cpi_mom < -0.1:
            signals.append(0.5)
            details["CPI Momentum"] = f"✅ Falling ({cpi_mom:+.2f}%)"
        elif cpi_mom > 0.2:
            signals.append(-0.5)
            details["CPI Momentum"] = f"🟠 Rising ({cpi_mom:+.2f}%)"
        else:
            signals.append(0)
            details["CPI Momentum"] = f"⚪ Stable ({cpi_mom:+.2f}%)"

    # 5. GDP Momentum
    gdp_data = _fetch(code, "gdp")
    if len(gdp_data) >= 2:
        gdp_change = gdp_data[0]["val"] - gdp_data[1]["val"]
        if gdp_change > 0:
            signals.append(1)
            details["GDP"] = f"✅ Growing"
        else:
            signals.append(-1)
            details["GDP"] = f"❌ Shrinking"

    # 6. Unemployment
    unemp_data = _fetch(code, "unemployment")
    if len(unemp_data) >= 2:
        unemp = unemp_data[0]["val"]
        prev_unemp = unemp_data[1]["val"]
        if unemp < 4:
            signals.append(1)
            details["Unemployment"] = f"✅ Low ({unemp:.1f}%)"
        elif unemp > 7:
            signals.append(-1)
            details["Unemployment"] = f"❌ High ({unemp:.1f}%)"
        else:
            signals.append(0)
            details["Unemployment"] = f"⚪ Moderate ({unemp:.1f}%)"

    # 7. Unemployment Momentum
    if len(unemp_data) >= 2:
        unemp_mom = unemp_data[0]["val"] - unemp_data[1]["val"]
        if unemp_mom < 0:
            signals.append(0.5)
            details["Unemployment Trend"] = f"✅ Falling ({unemp_mom:+.2f}%)"
        elif unemp_mom > 0:
            signals.append(-0.5)
            details["Unemployment Trend"] = f"🟠 Rising ({unemp_mom:+.2f}%)"
        else:
            signals.append(0)
            details["Unemployment Trend"] = f"⚪ Stable"

    # 8. Trade Balance
    trade_data = _fetch(code, "trade_balance")
    if len(trade_data) >= 2:
        trade = trade_data[0]["val"]
        prev_trade = trade_data[1]["val"]
        if trade > 0 and trade > prev_trade:
            signals.append(1)
            details["Trade Balance"] = f"✅ Surplus & Improving"
        elif trade > 0:
            signals.append(0.5)
            details["Trade Balance"] = f"🟡 Surplus"
        elif trade < 0 and trade < prev_trade:
            signals.append(-1)
            details["Trade Balance"] = f"❌ Deficit & Worsening"
        else:
            signals.append(-0.5)
            details["Trade Balance"] = f"🟠 Deficit"

    bullish = sum(1 for s in signals if s > 0)
    bearish = sum(1 for s in signals if s < 0)
    total = len(signals)
    score = round(sum(signals), 1)

    return {
        "score": score,
        "bullish": bullish,
        "bearish": bearish,
        "total": total,
        "details": details,
    }
