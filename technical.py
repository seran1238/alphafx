import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal
    return macd, signal, histogram

def calculate_bollinger(prices, period=20):
    ma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = ma + (2 * std)
    lower = ma - (2 * std)
    pct_b = (prices - lower) / (upper - lower)
    return upper, lower, pct_b

def calculate_stoch_rsi(prices, period=14):
    rsi = calculate_rsi(prices, period)
    min_rsi = rsi.rolling(period).min()
    max_rsi = rsi.rolling(period).max()
    stoch_rsi = (rsi - min_rsi) / (max_rsi - min_rsi)
    return stoch_rsi * 100

def calculate_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def get_technical_score(df):
    if df is None or len(df) < 30:
        return 0, {}

    close = df["close"]
    high = df["high"]
    low = df["low"]

    scores = {}

    # RSI
    rsi = calculate_rsi(close).iloc[-1]
    if rsi > 60:
        scores["RSI"] = 20
    elif rsi > 50:
        scores["RSI"] = 10
    elif rsi < 40:
        scores["RSI"] = -20
    elif rsi < 50:
        scores["RSI"] = -10
    else:
        scores["RSI"] = 0

    # MACD
    macd, signal, hist = calculate_macd(close)
    if hist.iloc[-1] > 0 and hist.iloc[-1] > hist.iloc[-2]:
        scores["MACD"] = 20
    elif hist.iloc[-1] > 0:
        scores["MACD"] = 10
    elif hist.iloc[-1] < 0 and hist.iloc[-1] < hist.iloc[-2]:
        scores["MACD"] = -20
    else:
        scores["MACD"] = -10

    # Bollinger Bands
    _, _, pct_b = calculate_bollinger(close)
    pb = pct_b.iloc[-1]
    if pb > 0.8:
        scores["Bollinger"] = 20
    elif pb > 0.5:
        scores["Bollinger"] = 10
    elif pb < 0.2:
        scores["Bollinger"] = -20
    else:
        scores["Bollinger"] = -10

    # Stochastic RSI
    stoch = calculate_stoch_rsi(close).iloc[-1]
    if stoch > 80:
        scores["StochRSI"] = 15
    elif stoch > 50:
        scores["StochRSI"] = 8
    elif stoch < 20:
        scores["StochRSI"] = -15
    else:
        scores["StochRSI"] = -8

    # Moving Averages
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    price = close.iloc[-1]
    if price > ma20 and price > ma50 and ma20 > ma50:
        scores["MA"] = 25
    elif price > ma20:
        scores["MA"] = 12
    elif price < ma20 and price < ma50:
        scores["MA"] = -25
    else:
        scores["MA"] = -12

    total = sum(scores.values())
    return total, scores
