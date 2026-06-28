import requests
from datetime import datetime, timedelta
from functools import lru_cache

FINNHUB_KEY = "d82th01r01ql4onfcqngd82th01r01ql4onfcqo0"

CURRENCY_COUNTRIES = {
    "USD": "US",
    "EUR": "EU",
    "GBP": "GB",
    "JPY": "JP",
    "CHF": "CH",
    "AUD": "AU",
    "CAD": "CA",
    "NZD": "NZ"
}

HIGH_IMPACT_EVENTS = [
    "interest rate", "rate decision", "cpi", "inflation",
    "gdp", "employment", "nonfarm", "payroll", "pmi",
    "retail sales", "trade balance"
]

@lru_cache(maxsize=1)
def get_economic_calendar():
    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    url = f"https://finnhub.io/api/v1/calendar/economic?from={today}&to={end}&token={FINNHUB_KEY}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("economicCalendar", [])
    except:
        pass
    return []

def get_upcoming_events(currency):
    country = CURRENCY_COUNTRIES.get(currency, "")
    events = get_economic_calendar()
    relevant = []
    for e in events:
        if e.get("country", "").upper() == country:
            event_name = e.get("event", "").lower()
            impact = e.get("impact", "")
            if impact == "high" or any(kw in event_name for kw in HIGH_IMPACT_EVENTS):
                relevant.append({
                    "date": e.get("time", "")[:10],
                    "event": e.get("event", ""),
                    "impact": impact,
                    "previous": e.get("prev", ""),
                    "estimate": e.get("estimate", "")
                })
    return relevant[:5]

def get_central_bank_bias(currency):
    """
    Zentralbank Bias — manuell gepflegt.
    Letzte Aktualisierung: 28. Juni 2026

    Quellen:
    - USD: Fed haelt 3.50-3.75% (Jun 17), dot plot hawkish (9/18 sehen Hike bis EOY)
    - EUR: ECB hiked auf 2.25% (Jun 11), erste Erhoehung seit Sep 2023, Hormuz-Schock
    - GBP: BOE haelt 3.75% (Jun 18), Bailey no rush, UK Inflation 2.8%
    - JPY: BOJ hiked auf 1.00% (Jun 16), 7-1 Vote, Yen-Verteidigung
    - CHF: SNB bei 0.25%, 2x gecut 2025, stabil
    - AUD: RBA haelt bei 4.35% (Jun 16), 3x geHIKED seit Jan 2026
    - CAD: BOC haelt 2.25%, US-Tariff-Unsicherheit bremst Cuts
    - NZD: RBNZ im Cutting-Zyklus, ~3.25%
    """
    BIAS = {
        "USD": {
            "bias": "Neutral",
            "last_change": "Hold",
            "rate": 3.625,
            "trend": "Holding",
            "note": "Hawkish dot plot - 9/18 sehen Hike bis EOY. Fed Chair Warsh Aera."
        },
        "EUR": {
            "bias": "Hawkish",
            "last_change": "Hike",
            "rate": 2.25,
            "trend": "Hiking",
            "note": "Erste Erhoehung seit Sep 2023 (Jun 11). Hormuz-Oelschock treibt HICP auf 3.0%."
        },
        "GBP": {
            "bias": "Neutral",
            "last_change": "Hold",
            "rate": 3.75,
            "trend": "Holding",
            "note": "BOE haelt (Jun 18), Bailey no rush. UK CPI 2.8%, Wachstum schwach."
        },
        "JPY": {
            "bias": "Hawkish",
            "last_change": "Hike",
            "rate": 1.00,
            "trend": "Hiking",
            "note": "BOJ hiked Jun 16 (7-1 Vote). Yen-Verteidigung + Inflationsrisiko."
        },
        "CHF": {
            "bias": "Neutral",
            "last_change": "Hold",
            "rate": 0.25,
            "trend": "Holding",
            "note": "SNB haelt nach 2 Cuts 2025. Naechster Entscheid Sep 2026."
        },
        "AUD": {
            "bias": "Hawkish",
            "last_change": "Hold",
            "rate": 4.35,
            "trend": "Hiking",
            "note": "RBA haelt Jun 16 nach 3 Hikes YTD 2026. Inflation noch zu hoch."
        },
        "CAD": {
            "bias": "Neutral",
            "last_change": "Hold",
            "rate": 2.25,
            "trend": "Holding",
            "note": "BOC haelt Jun 10. US-Tariff-Schock blockiert weitere Cuts."
        },
        "NZD": {
            "bias": "Dovish",
            "last_change": "Cut",
            "rate": 3.25,
            "trend": "Cutting",
            "note": "RBNZ im Cutting-Zyklus. Naechster Entscheid Jul 9, 2026."
        },
    }
    return BIAS.get(currency, {
        "bias": "Unknown",
        "last_change": "Unknown",
        "rate": 0,
        "trend": "Unknown",
        "note": ""
    })
