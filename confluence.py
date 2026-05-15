from calendar_data import get_central_bank_bias
from rate_differential import get_hawkish_dovish_ranking
from cot_extremes import get_cot_percentile
from yield_curve import get_yield_curve_score
from seasonality import get_seasonal_score
from political_risk import get_political_risk_score
from economic_regime import get_regime_bias
from config import CURRENCIES
from forex_pairs import get_trade_direction


def get_confluence_score(currency):
    signals = []
    reasons = []

    # 1. Central Bank Bias
    bias = get_central_bank_bias(currency)
    if bias["trend"] == "Hiking":
        signals.append(1)
        reasons.append(f"✅ CB Hiking ({bias['rate']}%)")
    elif bias["trend"] == "Cutting":
        signals.append(-1)
        reasons.append(f"❌ CB Cutting ({bias['rate']}%)")
    else:
        signals.append(0)
        reasons.append(f"⚪ CB Hold ({bias['rate']}%)")

    # 2. Rate Rank
    ranking = get_hawkish_dovish_ranking()
    position = next((i for i, r in enumerate(ranking) if r["currency"] == currency), 4)
    if position <= 1:
        signals.append(1)
        reasons.append(f"✅ High Rate Rank #{position + 1}")
    elif position >= 6:
        signals.append(-1)
        reasons.append(f"❌ Low Rate Rank #{position + 1}")
    else:
        signals.append(0)
        reasons.append(f"⚪ Mid Rate Rank #{position + 1}")

    # 3. COT Extremes
    if currency != "USD":
        cot = get_cot_percentile(currency)
        if cot:
            lm_pct = cot["lm_percentile"]
            if lm_pct <= 20:
                signals.append(1)
                reasons.append(f"✅ COT Extreme Short → Contrarian Bullish ({lm_pct:.0f}%ile)")
            elif lm_pct >= 80:
                signals.append(-1)
                reasons.append(f"❌ COT Extreme Long → Contrarian Bearish ({lm_pct:.0f}%ile)")
            elif lm_pct >= 60:
                signals.append(-0.5)
                reasons.append(f"🟡 COT High Long ({lm_pct:.0f}%ile)")
            elif lm_pct <= 40:
                signals.append(0.5)
                reasons.append(f"🟡 COT High Short ({lm_pct:.0f}%ile)")
            else:
                signals.append(0)
                reasons.append(f"⚪ COT Neutral ({lm_pct:.0f}%ile)")

    # 4. Yield Curve
    yc_score, yc_details = get_yield_curve_score(currency)
    yc_label = list(yc_details.values())[0] if yc_details else "N/A"
    if yc_score >= 20:
        signals.append(1)
        reasons.append(f"✅ {yc_label}")
    elif yc_score >= 10:
        signals.append(0.5)
        reasons.append(f"🟡 {yc_label}")
    elif yc_score <= -15:
        signals.append(-1)
        reasons.append(f"❌ {yc_label}")
    elif yc_score <= -5:
        signals.append(-0.5)
        reasons.append(f"🟠 {yc_label}")
    else:
        signals.append(0)
        reasons.append(f"⚪ {yc_label}")

    # 5. Political Risk
    pol_score, _ = get_political_risk_score(currency)
    if pol_score >= 20:
        signals.append(0.5)
        reasons.append(f"✅ Political Risk Low ({pol_score})")
    elif pol_score <= -20:
        signals.append(-1)
        reasons.append(f"❌ Political Risk High ({pol_score})")
    elif pol_score <= -10:
        signals.append(-0.5)
        reasons.append(f"🟠 Political Risk Elevated ({pol_score})")
    else:
        signals.append(0)
        reasons.append(f"⚪ Political Risk Neutral ({pol_score})")

    # 6. Seasonality
    seas_score, seas_signal, _, _ = get_seasonal_score(currency)
    if seas_score >= 5:
        signals.append(0.5)
        reasons.append(f"✅ {seas_signal}")
    elif seas_score <= -5:
        signals.append(-0.5)
        reasons.append(f"❌ {seas_signal}")
    else:
        signals.append(0)
        reasons.append(f"⚪ Seasonality Neutral ({seas_score})")

    # 7. Economic Regime (Dalio)
    regime_score, regime_label = get_regime_bias(currency)
    if regime_score >= 15:
        signals.append(1)
        reasons.append(f"✅ Regime Tailwind: {regime_label}")
    elif regime_score >= 5:
        signals.append(0.5)
        reasons.append(f"🟡 Regime Mild Tailwind: {regime_label}")
    elif regime_score <= -15:
        signals.append(-1)
        reasons.append(f"❌ Regime Headwind: {regime_label}")
    elif regime_score <= -5:
        signals.append(-0.5)
        reasons.append(f"🟠 Regime Mild Headwind: {regime_label}")
    else:
        signals.append(0)
        reasons.append(f"⚪ Regime Neutral: {regime_label}")

    # Aggregate
    bullish = sum(1 for s in signals if s > 0)
    bearish = sum(1 for s in signals if s < 0)
    total   = len(signals)

    cb_bullish          = signals[0] > 0 if signals else False
    cb_bearish          = signals[0] < 0 if signals else False
    cot_contrarian_bear = any("Contrarian Bearish" in r for r in reasons)
    cot_contrarian_bull = any("Contrarian Bullish" in r for r in reasons)

    if cb_bullish and cot_contrarian_bear:
        direction = "MIXED"
        strength  = "⚠️ Avoid — CB Bullish but COT Crowded Long"
    elif cb_bearish and cot_contrarian_bull:
        direction = "MIXED"
        strength  = "⚠️ Avoid — CB Bearish but COT Crowded Short"
    elif bullish >= total * 0.75:
        direction, strength = "BULLISH", "🟢 Strong"
    elif bullish >= total * 0.5:
        direction, strength = "BULLISH", "🟡 Moderate"
    elif bearish >= total * 0.75:
        direction, strength = "BEARISH", "🔴 Strong"
    elif bearish >= total * 0.5:
        direction, strength = "BEARISH", "🟠 Moderate"
    else:
        direction, strength = "NEUTRAL", "⚪ No Signal"

    return {
        "currency":      currency,
        "direction":     direction,
        "strength":      strength,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "total":         total,
        "reasons":       reasons,
    }


def get_best_confluences():
    results = [get_confluence_score(c) for c in CURRENCIES]
    bullish = [r for r in results if r["direction"] == "BULLISH" and "Strong" in r["strength"]]
    bearish = [r for r in results if r["direction"] == "BEARISH" and "Strong" in r["strength"]]

    setups = []
    for b in bullish:
        for s in bearish:
            trade = get_trade_direction(b["currency"], s["currency"])
            setups.append({
                "trade":          trade,
                "long":           b["currency"],
                "short":          s["currency"],
                "long_strength":  b["strength"],
                "short_strength": s["strength"],
                "long_reasons":   b["reasons"],
                "short_reasons":  s["reasons"],
                "confluence":     b["bullish_count"] + s["bearish_count"],
            })

    return sorted(setups, key=lambda x: x["confluence"], reverse=True)
