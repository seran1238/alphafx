import requests
import zipfile
import io
import pandas as pd
from functools import lru_cache

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
def load_historical_cot():
    dfs = []
    for year in [2023, 2024, 2025, 2026]:
        try:
            url = f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content))
                content = z.read(z.namelist()[0]).decode('utf-8', errors='ignore')
                df = pd.read_csv(io.StringIO(content))
                dfs.append(df)
        except:
            pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return None

def clean(val):
    try:
        return float(str(val).replace(',','').strip())
    except:
        return 0.0

def get_net_positioning(df, market):
    filtered = df[df["Market_and_Exchange_Names"].str.upper() == market.upper()].copy()
    if filtered.empty:
        return None
    filtered["date"] = pd.to_datetime(filtered["Report_Date_as_YYYY-MM-DD"])
    filtered = filtered.sort_values("date")

    filtered["lm_net"] = filtered["Lev_Money_Positions_Long_All"].apply(clean) - filtered["Lev_Money_Positions_Short_All"].apply(clean)
    filtered["am_net"] = filtered["Asset_Mgr_Positions_Long_All"].apply(clean) - filtered["Asset_Mgr_Positions_Short_All"].apply(clean)
    filtered["open_interest"] = filtered["Open_Interest_All"].apply(clean)

    # Net Change wöchentlich
    filtered["lm_change"] = filtered["Change_in_Lev_Money_Long_All"].apply(clean) - filtered["Change_in_Lev_Money_Short_All"].apply(clean)
    filtered["am_change"] = filtered["Change_in_Asset_Mgr_Long_All"].apply(clean) - filtered["Change_in_Asset_Mgr_Short_All"].apply(clean)
    filtered["oi_change"] = filtered["Open_Interest_All"].apply(clean).diff()

    return filtered[["date", "lm_net", "am_net", "lm_change", "am_change", "open_interest", "oi_change"]].reset_index(drop=True)

def get_cot_percentile(currency):
    market = COT_MARKETS.get(currency)
    if not market:
        return None

    df = load_historical_cot()
    if df is None:
        return None

    positioning = get_net_positioning(df, market)
    if positioning is None or len(positioning) < 10:
        return None

    current_lm = positioning["lm_net"].iloc[-1]
    current_am = positioning["am_net"].iloc[-1]
    current_lm_change = positioning["lm_change"].iloc[-1]
    current_am_change = positioning["am_change"].iloc[-1]
    current_oi = positioning["open_interest"].iloc[-1]
    current_oi_change = positioning["oi_change"].iloc[-1]

    lm_pct = (positioning["lm_net"] <= current_lm).mean() * 100
    am_pct = (positioning["am_net"] <= current_am).mean() * 100
    oi_pct = (positioning["open_interest"] <= current_oi).mean() * 100

    def get_extreme(pct):
        if pct >= 90:
            return "🔴 Extreme Long (Contrarian Bearish)"
        elif pct >= 75:
            return "🟡 High Long"
        elif pct <= 10:
            return "🔴 Extreme Short (Contrarian Bullish)"
        elif pct <= 25:
            return "🟡 High Short"
        else:
            return "⚪ Neutral"

    # Momentum Signal
    def get_momentum(change, net):
        if abs(net) < 1000:
            return "⚪ Flat"
        pct_change = change / abs(net) * 100 if net != 0 else 0
        if change > 5000:
            return "🟢 Strong Buying"
        elif change > 1000:
            return "🟡 Buying"
        elif change < -5000:
            return "🔴 Strong Selling"
        elif change < -1000:
            return "🟠 Selling"
        else:
            return "⚪ Flat"

    # OI Confirmation
    def get_oi_signal(oi_change, lm_change):
        if oi_change > 0 and lm_change > 0:
            return "✅ OI Rising + Long — Confirmed Bullish"
        elif oi_change > 0 and lm_change < 0:
            return "⚠️ OI Rising + Short — Confirmed Bearish"
        elif oi_change < 0 and lm_change > 0:
            return "🟡 OI Falling + Long — Weak Bullish"
        elif oi_change < 0 and lm_change < 0:
            return "🟡 OI Falling + Short — Weak Bearish"
        else:
            return "⚪ Neutral"

    return {
        "currency": currency,
        "lm_net": round(current_lm, 0),
        "lm_percentile": round(lm_pct, 1),
        "lm_extreme": get_extreme(lm_pct),
        "lm_change": round(current_lm_change, 0),
        "lm_momentum": get_momentum(current_lm_change, current_lm),
        "am_net": round(current_am, 0),
        "am_percentile": round(am_pct, 1),
        "am_extreme": get_extreme(am_pct),
        "am_change": round(current_am_change, 0),
        "open_interest": round(current_oi, 0),
        "oi_percentile": round(oi_pct, 1),
        "oi_change": round(current_oi_change, 0),
        "oi_signal": get_oi_signal(current_oi_change, current_lm_change),
        "history": positioning
    }
