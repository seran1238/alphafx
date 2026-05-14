import requests
import zipfile
import io
import pandas as pd
from functools import lru_cache

COT_URL = "https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip"

COT_MARKETS = {
    "EUR": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "GBP": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
    "JPY": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "CHF": "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",
    "AUD": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "CAD": "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "NZD": "NZ DOLLAR - CHICAGO MERCANTILE EXCHANGE",
}

@lru_cache(maxsize=1)
def load_cot_data():
    try:
        r = requests.get(COT_URL, timeout=15)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        content = z.read(z.namelist()[0]).decode('utf-8', errors='ignore')
        df = pd.read_csv(io.StringIO(content))
        return df
    except Exception as e:
        print(f"COT load error: {e}")
        return None

def get_cot_score(currency):
    if currency == "USD":
        scores = []
        for c in ["EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"]:
            s, _ = get_cot_score(c)
            scores.append(-s)
        avg = sum(scores) / len(scores) if scores else 0
        return avg, {"USD": "Inverse of majors"}

    market = COT_MARKETS.get(currency)
    if not market:
        return 0, {}

    df = load_cot_data()
    if df is None:
        return 0, {}

    try:
        name_col = "Market_and_Exchange_Names"
        filtered = df[df[name_col].str.upper() == market.upper()]

        if filtered.empty:
            return 0, {"Error": f"Market not found: {market}"}

        row = filtered.sort_values("Report_Date_as_YYYY-MM-DD", ascending=False).iloc[0]

        # Asset Manager (grosse Fonds)
        am_long = float(str(row["Asset_Mgr_Positions_Long_All"]).replace(',',''))
        am_short = float(str(row["Asset_Mgr_Positions_Short_All"]).replace(',',''))
        am_net = am_long - am_short
        am_total = am_long + am_short
        am_pct = (am_net / am_total * 100) if am_total > 0 else 0

        # Leveraged Money (Hedge Funds)
        lm_long = float(str(row["Lev_Money_Positions_Long_All"]).replace(',',''))
        lm_short = float(str(row["Lev_Money_Positions_Short_All"]).replace(',',''))
        lm_net = lm_long - lm_short
        lm_total = lm_long + lm_short
        lm_pct = (lm_net / lm_total * 100) if lm_total > 0 else 0

        # Dealer (Banken)
        d_long = float(str(row["Dealer_Positions_Long_All"]).replace(',',''))
        d_short = float(str(row["Dealer_Positions_Short_All"]).replace(',',''))
        d_net = d_long - d_short
        d_total = d_long + d_short
        d_pct = (d_net / d_total * 100) if d_total > 0 else 0

        score = 0
        details = {}

        # Asset Manager Score (40%)
        if am_pct > 15:
            score += 40
            details["Asset Mgr"] = f"+40 (Net Long {am_pct:.1f}%)"
        elif am_pct > 0:
            score += 20
            details["Asset Mgr"] = f"+20 (Slightly Long {am_pct:.1f}%)"
        elif am_pct < -15:
            score -= 40
            details["Asset Mgr"] = f"-40 (Net Short {am_pct:.1f}%)"
        else:
            score -= 20
            details["Asset Mgr"] = f"-20 (Slightly Short {am_pct:.1f}%)"

        # Leveraged Money Score (35%)
        if lm_pct > 15:
            score += 35
            details["Hedge Funds"] = f"+35 (Net Long {lm_pct:.1f}%)"
        elif lm_pct > 0:
            score += 15
            details["Hedge Funds"] = f"+15 (Slightly Long {lm_pct:.1f}%)"
        elif lm_pct < -15:
            score -= 35
            details["Hedge Funds"] = f"-35 (Net Short {lm_pct:.1f}%)"
        else:
            score -= 15
            details["Hedge Funds"] = f"-15 (Slightly Short {lm_pct:.1f}%)"

        # Dealer Score (25%) - Dealer sind oft contrarian
        if d_pct < -15:
            score += 25
            details["Dealers"] = f"+25 (Short {d_pct:.1f}% - Contrarian Bullish)"
        elif d_pct < 0:
            score += 10
            details["Dealers"] = f"+10 (Slightly Short {d_pct:.1f}%)"
        elif d_pct > 15:
            score -= 25
            details["Dealers"] = f"-25 (Long {d_pct:.1f}% - Contrarian Bearish)"
        else:
            score -= 10
            details["Dealers"] = f"-10 (Slightly Long {d_pct:.1f}%)"

        return score, details

    except Exception as e:
        return 0, {"Error": str(e)}
