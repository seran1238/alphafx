import requests
from functools import lru_cache

COUNTRY_FIPS = {
    "USD": ["US"],
    "EUR": ["GM", "FR", "IT", "SP", "NL", "BE", "AT", "PO", "FI", "GR"],
    "GBP": ["UK"],
    "JPY": ["JA"],
    "CHF": ["SZ"],
    "AUD": ["AS"],
    "CAD": ["CA"],
    "NZD": ["NZ"],
}

RISK_KEYWORDS = {
    "negative": [
        "crisis", "resign", "collapse", "crash", "recession", "default",
        "scandal", "protest", "strike", "war", "conflict", "sanction",
        "deficit", "stagflation", "political uncertainty", "no confidence",
        "snap election", "tariff", "coup", "emergency",
    ],
    "positive": [
        "growth", "surplus", "reform", "recovery", "strong", "beat",
        "exceed", "stability", "confidence", "expansion", "trade deal",
        "agreement", "stimulus",
    ],
}

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


@lru_cache(maxsize=8)
def get_political_risk_score(currency):
    codes = COUNTRY_FIPS.get(currency)
    if not codes:
        return 0, []

    country_filter = " OR ".join(f"sourcecountry:{c}" for c in codes)

    params = {
        "query": country_filter,
        "mode": "ArtList",
        "maxrecords": "75",
        "format": "json",
        "timespan": "7d",
        "sort": "DateDesc",
    }

    try:
        r = requests.get(GDELT_DOC_URL, params=params, timeout=12)
        if r.status_code != 200:
            return 0, [f"GDELT HTTP {r.status_code}"]

        articles = r.json().get("articles", [])
        if not articles:
            return 0, []

        tone_values = []
        headlines = []

        for art in articles:
            title = art.get("title", "")
            tone_raw = art.get("tone", "")
            if not tone_raw:
                continue
            try:
                tone_val = float(str(tone_raw).split(",")[0])
                tone_values.append(tone_val)

                txt = title.lower()
                neg = sum(1 for kw in RISK_KEYWORDS["negative"] if kw in txt)
                pos = sum(1 for kw in RISK_KEYWORDS["positive"] if kw in txt)
                if neg > pos or tone_val < -3:
                    headlines.append(f"🔴 {title[:90]}")
                elif pos > neg or tone_val > 3:
                    headlines.append(f"🟢 {title[:90]}")

            except (ValueError, IndexError):
                continue

        if not tone_values:
            return 0, []

        avg_tone = sum(tone_values) / len(tone_values)
        score = int(avg_tone * 9)
        score = max(-100, min(100, score))
        return score, headlines[:6]

    except Exception as e:
        return 0, [f"GDELT error: {e}"]


def get_political_risk_label(score):
    if score >= 20:
        return "🟢 Low Risk"
    elif score >= 0:
        return "🟡 Neutral"
    elif score >= -20:
        return "🟠 Elevated Risk"
    else:
        return "🔴 High Risk"
