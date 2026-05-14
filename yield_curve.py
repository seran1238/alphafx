import requests
from config import FRED_KEY

YIELD_SERIES = {
    "USD": {"2y": "DGS2", "10y": "DGS10"},
    "EUR": {"2y": None, "10y": "IRLTLT01EZM156N"},
    "GBP": {"2y": None, "10y": "IRLTLT01GBM156N"},
    "JPY": {"2y": None, "10y": "IRLTLT01JPM156N"},
    "CHF": {"2y": None, "10y": "IRLTLT01CHM156N"},
    "AUD": {"2y": None, "10y": "IRLTLT01AUM156N"},
    "CAD": {"2y": None, "10y": "IRLTLT01CAM156N"},
    "NZD": {"2y": None, "10y": "IRLTLT01NZM156N"},
}

# Zentralbank Rate als Proxy für 2y wenn keine Daten
CB_RATES = {
    "USD": 3.625, "EUR": 2.00, "GBP": 3.75,
    "JPY": 0.75, "CHF": 0.00, "AUD": 4.35,
    "CAD": 2.75, "NZD": 2.25
}

def get_fred(series_id, limit=2):
    if not series_id:
        return []
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit={limit}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if "observations" in data:
            return [float(o["value"]) for o in data["observations"] if o["value"] != "."]
    except:
        pass
    return []

def get_yield_curve_score(currency):
    series = YIELD_SERIES.get(currency, {})
    score = 0
    details = {}

    y10_data = get_fred(series.get("10y"))
    y2_data = get_fred(series.get("2y"))

    # Nutze CB Rate als Proxy für 2y wenn keine Daten
    y10 = y10_data[0] if y10_data else None
    y2 = y2_data[0] if y2_data else CB_RATES.get(currency)

    if y10 and y2:
        spread = y10 - y2
        if spread > 0.5:
            score += 20
            details["Yield Curve"] = f"✅ Normal +{spread:.2f}% — Growth Expected"
        elif spread > 0:
            score += 10
            details["Yield Curve"] = f"🟡 Flat +{spread:.2f}% — Uncertain"
        elif spread > -0.5:
            score -= 10
            details["Yield Curve"] = f"🟠 Slightly Inverted {spread:.2f}%"
        else:
            score -= 25
            details["Yield Curve"] = f"🔴 Inverted {spread:.2f}% — Recession Risk"

        if len(y10_data) >= 2 and y2:
            prev_spread = y10_data[1] - y2
            if spread > prev_spread:
                score += 5
                details["YC Trend"] = "📈 Steepening"
            else:
                score -= 5
                details["YC Trend"] = "📉 Flattening"
    elif y10:
        details["Yield Curve"] = f"10y: {y10:.2f}% (no 2y data)"
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
            "trend": details.get("YC Trend", "N/A")
        })
    return results
