"""
backtesting.py  —  AlphaFX
Backtesting: CB Signal Performance via CME Currency Futures (Yahoo Finance)
"""

import requests
import pandas as pd
import yfinance as yf
from config import FXMACRO_KEY

BASE_MACRO = "https://api.fxmacrodata.com/v1"

PAIRS = {
    "EUR": "6E=F",
    "GBP": "6B=F",
    "JPY": "6J=F",
    "AUD": "6A=F",
    "CAD": "6C=F",
    "CHF": "6S=F",
    "NZD": "6N=F",
}

CURRENCY_MAP = {
    "EUR": "eur", "GBP": "gbp", "JPY": "jpy",
    "AUD": "aud", "CAD": "cad", "CHF": "chf", "NZD": "nzd",
}

_fx_cache = {}
_macro_cache = {}


def get_fx_weekly(ticker):
    if ticker in _fx_cache:
        return _fx_cache[ticker]
    try:
        data = yf.download(ticker, period="5y", interval="1wk", progress=False)
        if data.empty:
            return pd.DataFrame()
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
        data = data.reset_index()
        rows = [{"date": str(r["Date"])[:10], "close": float(r["Close"])} for _, r in data.iterrows()]
        result = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        _fx_cache[ticker] = result
        return result
    except Exception:
        return pd.DataFrame()


def get_macro_history(code, indicator, limit=52):
    key = f"{code}_{indicator}"
    if key in _macro_cache:
        return _macro_cache[key]
    try:
        url = f"{BASE_MACRO}/announcements/{code}/{indicator}?api_key={FXMACRO_KEY}&limit={limit}"
        r = requests.get(url, timeout=15)
        data = r.json().get("data", [])
        rows = [{"date": d["date"], "val": d["val"]} for d in data]
        result = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        _macro_cache[key] = result
        return result
    except Exception:
        return pd.DataFrame()


def get_yield_curve_history(code):
    """Get historical 10y - 2y spread"""
    y10 = get_macro_history(code, "gov_bond_10y", limit=52)
    y2  = get_macro_history(code, "gov_bond_2y",  limit=52)
    if y10.empty:
        return pd.DataFrame()
    result = []
    for _, row in y10.iterrows():
        date = row["date"]
        y2_at = y2[y2["date"] <= date] if not y2.empty else pd.DataFrame()
        y2_val = y2_at.iloc[-1]["val"] if not y2_at.empty else None
        spread = row["val"] - y2_val if y2_val is not None else None
        if spread is not None:
            result.append({"date": date, "spread": spread})
    return pd.DataFrame(result).sort_values("date").reset_index(drop=True)


def compute_simple_signal(currency):
    code = CURRENCY_MAP.get(currency)
    if not code:
        return pd.DataFrame()

    rate_df = get_macro_history(code, "policy_rate", limit=52)
    cpi_df  = get_macro_history(code, "inflation",   limit=52)
    gdp_df  = get_macro_history(code, "gdp",         limit=52)
    yc_df   = get_yield_curve_history(code)

    if rate_df.empty:
        return pd.DataFrame()

    signals = []
    for i in range(1, len(rate_df)):
        date        = rate_df.iloc[i]["date"]
        rate_change = rate_df.iloc[i]["val"] - rate_df.iloc[i-1]["val"]

        # CPI momentum
        cpi_at  = cpi_df[cpi_df["date"] <= date] if not cpi_df.empty else pd.DataFrame()
        cpi_mom = (cpi_at.iloc[-1]["val"] - cpi_at.iloc[-2]["val"]) if len(cpi_at) >= 2 else 0

        # GDP momentum
        gdp_at  = gdp_df[gdp_df["date"] <= date] if not gdp_df.empty else pd.DataFrame()
        gdp_mom = (gdp_at.iloc[-1]["val"] - gdp_at.iloc[-2]["val"]) if len(gdp_at) >= 2 else 0

        # Yield Curve
        yc_at   = yc_df[yc_df["date"] <= date] if not yc_df.empty else pd.DataFrame()
        yc_spread = yc_at.iloc[-1]["spread"] if not yc_at.empty else 0

        score = 0
        # CB Rate momentum (strongest signal)
        if rate_change > 0:   score += 2
        elif rate_change < 0: score -= 2

        # CPI — falling inflation = good for currency
        if cpi_mom < -0.1:    score += 0.5
        elif cpi_mom > 0.3:   score -= 0.5

        # GDP growth
        if gdp_mom > 0:       score += 1
        elif gdp_mom < 0:     score -= 1

        # Yield Curve — normal = bullish, inverted = bearish
        if yc_spread > 0.5:   score += 0.5
        elif yc_spread < 0:   score -= 0.5

        signal = 1 if score > 1 else -1 if score < -1 else 0
        if signal != 0:
            signals.append({"date": date, "signal": signal, "score": round(score, 1)})

    return pd.DataFrame(signals).sort_values("date").reset_index(drop=True)


def run_backtest(currency, forward_weeks=4):
    ticker = PAIRS.get(currency)
    if not ticker:
        return None

    fx_df  = get_fx_weekly(ticker)
    sig_df = compute_simple_signal(currency)

    if fx_df.empty or sig_df.empty:
        return None

    results = []
    for _, row in sig_df.iterrows():
        sig_date = row["date"]
        signal   = row["signal"]

        fx_at  = fx_df[fx_df["date"] <= sig_date]
        fx_fwd = fx_df[fx_df["date"] >= sig_date]

        if fx_at.empty or len(fx_fwd) < forward_weeks:
            continue

        price_entry = fx_at.iloc[-1]["close"]
        price_exit  = fx_fwd.iloc[forward_weeks - 1]["close"]
        pct_change  = (price_exit - price_entry) / price_entry * 100

        correct = (signal == 1 and pct_change > 0) or (signal == -1 and pct_change < 0)
        results.append({
            "date":       sig_date,
            "signal":     "🟢 Bullish" if signal == 1 else "🔴 Bearish",
            "entry":      round(price_entry, 5),
            "exit":       round(price_exit,  5),
            "pct_change": round(pct_change,  3),
            "correct":    correct,
        })

    if not results:
        return None

    df       = pd.DataFrame(results)
    total    = len(df)
    correct  = int(df["correct"].sum())
    hit_rate = round(correct / total * 100, 1) if total > 0 else 0
    avg_gain = round(df[df["correct"]]["pct_change"].mean(), 3) if correct > 0 else 0
    avg_loss = round(df[~df["correct"]]["pct_change"].mean(), 3) if (total - correct) > 0 else 0

    return {
        "df":       df,
        "total":    total,
        "correct":  correct,
        "hit_rate": hit_rate,
        "avg_gain": avg_gain,
        "avg_loss": avg_loss,
    }
