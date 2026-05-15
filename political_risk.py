import requests
from datetime import datetime, timedelta
from functools import lru_cache
from calendar_data import FINNHUB_KEY

COUNTRY_KEYWORDS = {
    "USD": ["federal reserve", "fed", "us economy", "white house", "congress", "treasury", "powell"],
    "EUR": ["ecb", "european central bank", "eurozone", "eu economy", "draghi", "lagarde"],
    "GBP": ["bank of england", "boe", "uk economy", "downing street", "prime minister", "starmer", "labour", "conservative"],
    "JPY": ["bank of japan", "boj", "japan economy", "yen", "kishida", "ueda"],
    "CHF": ["snb", "swiss national bank", "switzerland economy", "swiss franc"],
    "AUD": ["rba", "reserve bank australia", "australia economy", "aussie"],
    "CAD": ["bank of canada", "boc", "canada economy", "trudeau", "carney"],
    "NZD": ["rbnz", "reserve bank new zealand", "new zealand economy", "kiwi"]
}

RISK_KEYWORDS = {
    "negative": ["crisis", "resign", "collapse", "crash", "recession", "default", "scandal", 
                 "protest", "strike", "war", "conflict", "sanction", "deficit", "debt",
                 "inflation surge", "rate hike", "stagflation", "political uncertainty",
                 "leadership challenge", "no confidence", "snap election"],
    "positive": ["growth", "surplus", "reform", "recovery", "strong", "beat", "exceed",
                 "stability", "confidence", "expansion", "trade deal", "agreement"]
}

@lru_cache(maxsize=8)
def get_political_risk_score(currency):
    keywords = COUNTRY_KEYWORDS.get(currency, [])
    if not keywords:
        return 0, []

    score = 0
    headlines = []

    try:
        # Suche News der letzten 7 Tage
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        url = f"https://finnhub.io/api/v1/news?category=general&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return 0, []

        news = r.json()

        for article in news[:50]:
            headline = article.get("headline", "").lower()
            summary = article.get("summary", "").lower()
            text = headline + " " + summary

            # Prüfe ob Artikel relevant für diese Währung ist
            relevant = any(kw in text for kw in keywords)
            if not relevant:
                continue

            # Zähle negative und positive Keywords
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

    # Normalisiere Score zwischen -100 und +100
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
