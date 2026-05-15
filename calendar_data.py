import requests
from datetime import datetime, timedelta
from functools import lru_cache

# Finnhub kostenlose API für Wirtschaftskalender
# Registriere dich auf finnhub.io und hole dir einen kostenlosen Key
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
    # Basierend auf letzten Zinsentscheiden und Forward Guidance
    # Diese Daten werden manuell gepflegt und wöchentlich aktualisiert
    # In einer späteren Version via NLP aus Zentralbank-Statements extrahiert
    BIAS = {
        "USD": {"bias": "Dovish", "last_change": "Cut", "rate": 4.33, "trend": "Cutting"},
        "EUR": {"bias": "Dovish", "last_change": "Cut", "rate": 2.40, "trend": "Cutting"},
        "GBP": {"bias": "Dovish", "last_change": "Cut", "rate": 4.25, "trend": "Cutting"},
        "JPY": {"bias": "Hawkish", "last_change": "Hike", "rate": 0.50, "trend": "Hiking"},
        "CHF": {"bias": "Dovish", "last_change": "Cut", "rate": 0.25, "trend": "Cutting"},
        "AUD": {"bias": "Dovish", "last_change": "Cut", "rate": 4.10, "trend": "Cutting"},
        "CAD": {"bias": "Dovish", "last_change": "Cut", "rate": 2.75, "trend": "Cutting"},
        "NZD": {"bias": "Dovish", "last_change": "Cut", "rate": 3.50, "trend": "Cutting"},
    }
    return BIAS.get(currency, {"bias": "Unknown", "last_change": "Unknown", "rate": 0, "trend": "Unknown"})
