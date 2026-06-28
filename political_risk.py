import requests
from datetime import datetime, timedelta
from functools import lru_cache
from calendar_data import FINNHUB_KEY

COUNTRY_KEYWORDS = {
    "USD": ["federal reserve", "fed", "us economy", "white house", "congress", "treasury", "powell", "warsh"],
    "EUR": ["ecb", "european central bank", "eurozone", "eu economy", "lagarde"],
    "GBP": ["bank of england", "boe", "uk economy", "downing street", "prime minister", "starmer", "labour"],
    "JPY": ["bank of japan", "boj", "japan economy", "yen", "ueda", "himino"],
    "CHF": ["snb", "swiss national bank", "switzerland economy", "swiss franc"],
    "AUD": ["rba", "reserve bank australia", "australia economy", "aussie"],
    "CAD": ["bank of canada", "boc", "canada economy", "macklem", "carney"],
    "NZD": ["rbnz", "reserve bank new zealand", "new zealand economy", "kiwi"]
}

RISK_KEYWORDS = {
    "negative": ["crisis", "resign", "collapse", "crash", "recession", "default", "scandal",
                 "protest", "strike", "war", "conflict", "sanction", "deficit", "debt",
                 "inflation surge", "stagflation", "political uncertainty",
                 "leadership challenge", "no confidence", "snap election", "tariff", "hormuz"],
    "positive": ["growth", "surplus", "reform", "recovery", "strong", "beat", "exceed",
                 "stability", "confidence", "expansion", "trade deal", "agreement", "hike"]
}

GDELT_THEMES = {
    "USD": "ECON_CENTRALBANK+TAX_FNCACT_FEDERAL+USGOV",
    "EUR": "ECON_CENTRALBANK+EU",
    "GBP": "ECON_CENTRALBANK+UKENGLISH",
    "JPY": "ECON_CENTRALBANK+JAPAN",
    "CHF": "ECON_CENTRALBANK+SWITZERLAND",
    "AUD": "ECON_CENTRALBANK+AUSTRALIA",
    "CAD": "ECON_CENTRALBANK+CANADA",
    "NZD": "ECON_CENTRALBANK+NEWZEALAND",
}

@lru_cache(maxsize=8)
def get_gdelt_tone(currency):
    """Holt durchschnittlichen Tone-Score aus GDELT GKG fuer diese Waehrung."""
    try:
        keyword = COUNTRY_KEYWORDS.get(currency, [])[0]
        url = (
            f"https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={keyword}+sourcecountry:US&mode=artlist&maxrecords=25"
            f"&format=json&timespan=3d"
        )
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            articles = data.get("articles", [])
            if articles:
                tones = []
                for a in articles:
                    tone_str = a.get("tone", "")
                    if tone_str:
                        try:
                            tone_val = float(tone_str.split(",")[0])
                            tones.append(tone_val)
                        except:
                            pass
                if tones:
                    avg_tone = sum(tones) / len(tones)
                    # GDELT Tone: negativ = schlechte News, positiv = gute News
                    # Skalieren auf -100 bis +100
                    score = max(-100, min(100, avg_tone * 5))
                    return round(score, 1)
    except:
        pass
    return None

@lru_cache(maxsize=8)
def get_political_risk_score(currency):
    headlines = []
    score = 0

    # Versuch 1: GDELT
    gdelt_score = get_gdelt_tone(currency)
    if gdelt_score is not None:
        return gdelt_score, [f"📡 GDELT Tone Score: {gdelt_score:+.1f}"]

    # Fallback: Finnhub
    keywords = COUNTRY_KEYWORDS.get(currency, [])
    try:
        url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            news = r.json()
            for article in news[:50]:
                headline = article.get("headline", "").lower()
                summary = article.get("summary", "").lower()
                text = headline + " " + summary
                relevant = any(kw in text for kw in keywords)
                if not relevant:
                    continue
                neg_count = sum(1 for kw in RISK_KEYWORDS["negative"] if kw in text)
                pos_count = sum(1 for kw in RISK_KEYWORDS["positive"] if kw in text)
                if neg_count > pos_count:
                    score -= neg_count * 5
                    headlines.append(f"🔴 {article.get('headline', '')[:80]}")
                elif pos_count > neg_count:
                    score += pos_count * 5
                    headlines.append(f"🟢 {article.get('headline', '')[:80]}")
    except Exception as e:
        return 0, [f"Error: {str(e)}"]

    score = max(-100, min(100, score))
    return score, headlines[:5]

def get_political_risk_label(score):
    if score >= 20:
        return "🟢 Low Risk"
    elif score >= 0:
        return "🟡 Neutral"
    elif score >= -20:
        return "🟠 Elevated Risk"
    else:
        return "🔴 High Risk"
