import requests
from functools import lru_cache
from config import FRED_KEY

IP_SERIES = {
    "USD": "INDPRO",
    "EUR": "PRMNTO01EZM659S",
    "GBP": "GBRPROINDMISMEI",
    "JPY": "JPNPROINDMISMEI",
    "CHF": "CHEPROINDMISMEI",
    "AUD": "AUSPROINDMISMEI",
    "CAD": "CANPROINDMISMEI",
    "NZD": "NZLPROINDMISMEI",
}

CPI_SERIES = {
    "USD": "CPIAUCSL",
    "EUR": "CP0000EZ19M086NEST",
    "GBP": "GBRCPIALLMINMEI",
    "JPY": "JPNCPIALLMINMEI",
    "CHF": "CHECPIALLMINMEI",
    "AUD": "AUSCPIALLMINMEI",
    "CAD": "CANCPIALLMINMEI",
    "NZD": "NZLCPIALLMINMEI",
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


def _fetch_fred(series_id, limit=7):
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={FRED_KEY}"
        f"&file_type=json&sort_order=desc&limit={limit}"
    )
    try:
        r = requests.get(url, timeout=6)
        return [
            float(o["value"])
            for o in r.json().get("observations", [])
            if o["value"] != "."
        ]
    except Exception:
        return []


def _momentum(series, periods=3):
    if len(series) <= periods:
        return None
    latest, prior = series[0], series[periods]
    return ((latest - prior) / abs(prior)) * 100 if prior != 0 else None


@lru_cache(maxsize=4)
def get_regime(anchor="USD"):
    ip_data  = _fetch_fred(IP_SERIES.get(anchor,  "INDPRO"))
    cpi_data = _fetch_fred(CPI_SERIES.get(anchor, "CPIAUCSL"))

    growth_mom    = _momentum(ip_data,  3)
    inflation_mom = _momentum(cpi_data, 3)

    growth_rising    = growth_mom    is not None and growth_mom    > 0
    inflation_rising = inflation_mom is not None and inflation_mom > 0

    name, emoji, desc = REGIME_META[(growth_rising, inflation_rising)]

    return {
        "regime":        name,
        "emoji":         emoji,
        "description":   desc,
        "growth_mom":    round(growth_mom,    3) if growth_mom    is not None else None,
        "inflation_mom": round(inflation_mom, 3) if inflation_mom is not None else None,
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
