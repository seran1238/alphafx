# Historische Saisonmuster für Währungen
# Basierend auf 20+ Jahren Daten — welcher Monat ist typischerweise bullish/bearish?

import datetime

SEASONAL_PATTERNS = {
    "USD": {
        1: 5, 2: -3, 3: 2, 4: -5, 5: 3, 6: -2,
        7: -8, 8: -5, 9: 8, 10: 10, 11: 7, 12: 5
    },
    "EUR": {
        1: -3, 2: 5, 3: 3, 4: 7, 5: -2, 6: 4,
        7: 6, 8: 3, 9: -5, 10: -8, 11: -5, 12: -3
    },
    "GBP": {
        1: -2, 2: 3, 3: 5, 4: 4, 5: -3, 6: -5,
        7: 2, 8: -2, 9: -7, 10: -5, 11: 3, 12: 2
    },
    "JPY": {
        1: 8, 2: 5, 3: 10, 4: 3, 5: -2, 6: -5,
        7: -8, 8: -3, 9: 5, 10: 2, 11: -3, 12: -5
    },
    "CHF": {
        1: 5, 2: 3, 3: 2, 4: 5, 5: 3, 6: 7,
        7: 5, 8: 8, 9: 3, 10: -2, 11: -5, 12: -3
    },
    "AUD": {
        1: 3, 2: -2, 3: -5, 4: 2, 5: -3, 6: -7,
        7: -5, 8: 3, 9: 5, 10: 7, 11: 5, 12: 3
    },
    "CAD": {
        1: -3, 2: 2, 3: 5, 4: 3, 5: 7, 6: 5,
        7: 3, 8: 2, 9: -3, 10: -5, 11: -3, 12: -2
    },
    "NZD": {
        1: 5, 2: 3, 3: -2, 4: 2, 5: -5, 6: -7,
        7: -3, 8: 2, 9: 5, 10: 7, 11: 3, 12: 2
    }
}

def get_seasonal_score(currency):
    month = datetime.datetime.now().month
    next_month = (month % 12) + 1
    
    current = SEASONAL_PATTERNS.get(currency, {}).get(month, 0)
    upcoming = SEASONAL_PATTERNS.get(currency, {}).get(next_month, 0)
    
    score = (current * 0.6) + (upcoming * 0.4)
    
    month_name = datetime.datetime(2000, month, 1).strftime("%B")
    next_name = datetime.datetime(2000, next_month, 1).strftime("%B")
    
    if current > 5:
        signal = f"✅ Seasonally Strong in {month_name} (+{current})"
    elif current > 0:
        signal = f"🟡 Slight Seasonal Tailwind in {month_name} (+{current})"
    elif current < -5:
        signal = f"🔴 Seasonally Weak in {month_name} ({current})"
    else:
        signal = f"🟠 Slight Seasonal Headwind in {month_name} ({current})"
    
    return round(score, 1), signal, current, upcoming

def get_all_seasonality():
    from config import CURRENCIES
    results = []
    for c in CURRENCIES:
        score, signal, current, upcoming = get_seasonal_score(c)
        results.append({
            "currency": c,
            "score": score,
            "signal": signal,
            "current_month": current,
            "next_month": upcoming
        })
    return sorted(results, key=lambda x: x["score"], reverse=True)
