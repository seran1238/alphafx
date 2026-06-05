from calendar_data import get_central_bank_bias
from rate_differential import get_hawkish_dovish_ranking
from cot_extremes import get_cot_percentile
from yield_curve import get_yield_curve_score
from seasonality import get_seasonal_score
from political_risk import get_political_risk_score, get_political_risk_label
from macro import get_macro_score
from config import CURRENCIES
from forex_pairs import get_trade_direction

WEIGHTS = {
    "cb":          0.30,
    "macro":       0.25,
    "cot":         0.20,
    "yield":       0.15,
    "seasonality": 0.05,
    "event":       0.05,
}

def _strength_label(net_score):
    abs_score = abs(net_score)
    if abs_score >= 75:
        return "Very Strong"
    elif abs_score >= 55:
        return "Strong"
    elif abs_score >= 35:
        return "Moderate"
    elif abs_score >= 15:
        return "Weak"
    else:
        return "No Signal"

def _signal_category(direction, strength, conflicts):
    if direction == "NEUTRAL" or strength == "No Signal":
        return "🚫 No Trade"
    if conflicts:
        return "⚠️ Mixed / Avoid"
    if strength in ("Very Strong", "Strong"):
        return f"✅ Clean {'Long' if direction == 'BULLISH' else 'Short'}"
    return f"🟡 Weak {'Long' if direction == 'BULLISH' else 'Short'}"

def _macro_label(raw, norm):
    if norm > 0.5:
        return f"✅ Macro Tailwind (score: {raw:+.0f})"
    elif norm > 0.1:
        return f"🟡 Macro Mild Tailwind (score: {raw:+.0f})"
    elif norm < -0.5:
        return f"❌ Macro Headwind (score: {raw:+.0f})"
    elif norm < -0.1:
        return f"🟠 Macro Mild Headwind (score: {raw:+.0f})"
    else:
        return f"⚪ Macro Neutral (score: {raw:+.0f})"

def _build_explanation(currency, direction, details, conflicts, strength):
    lines = [f"{currency} receives a {direction.lower()} signal ({strength}) because:"]
    for key in ["cb", "macro", "cot", "yield", "seasonality"]:
        label = details.get(key, "")
        if label:
            lines.append(f"  • {label}")
    if conflicts:
        lines.append("Conflicts:")
        for c in conflicts:
            lines.append(f"  • {c}")
    return "\n".join(lines)

def get_confluence_score(currency):
    reasons = []
    conflicts = []
    component_scores = {}
    component_details = {}

    # 1. Central Bank / Rates (30%)
    bias = get_central_bank_bias(currency)
    ranking = get_hawkish_dovish_ranking()
    position = next((i for i, r in enumerate(ranking) if r["currency"] == currency), 4)

    if bias["trend"] == "Hiking":
        cb_score = 1.0
        cb_label = f"✅ CB Hiking ({bias['rate']}%)"
    elif bias["trend"] == "Cutting":
        cb_score = -1.0
        cb_label = f"❌ CB Cutting ({bias['rate']}%)"
    else:
        cb_score = 0.0
        cb_label = f"⚪ CB Hold ({bias['rate']}%)"

    if position <= 1:
        cb_score = min(1.0, cb_score + 0.2)
        cb_label += f" | ✅ Rate Rank #{position+1}"
    elif position >= 6:
        cb_score = max(-1.0, cb_score - 0.2)
        cb_label += f" | ❌ Rate Rank #{position+1}"
    else:
        cb_label += f" | ⚪ Mid Rate Rank #{position+1}"

    component_scores["cb"] = cb_score
    component_details["cb"] = cb_label
    reasons.append(cb_label)

    # 2. Macro Regime (25%)
    macro_raw, macro_details = get_macro_score(currency)
    macro_norm = max(-1.0, min(1.0, macro_raw / 60.0))
    macro_label = _macro_label(macro_raw, macro_norm)
    component_scores["macro"] = macro_norm
    component_details["macro"] = macro_label
    reasons.append(macro_label)

    # 3. COT (20%)
    cot_score = 0.0
    cot_label = "⚪ COT N/A"
    if currency != "USD":
        cot = get_cot_percentile(currency)
        if cot:
            pct = cot["lm_percentile"]
            if pct <= 10:
                cot_score = 1.0
                cot_label = f"✅ COT Extreme Short → Contrarian Bullish ({pct:.0f}%ile)"
            elif pct <= 20:
                cot_score = 0.7
                cot_label = f"✅ COT Very Short → Contrarian Bullish ({pct:.0f}%ile)"
            elif pct <= 40:
                cot_score = 0.3
                cot_label = f"🟡 COT High Short ({pct:.0f}%ile)"
            elif pct <= 60:
                cot_score = 0.0
                cot_label = f"⚪ COT Neutral ({pct:.0f}%ile)"
            elif pct <= 80:
                cot_score = -0.3
                cot_label = f"🟡 COT High Long ({pct:.0f}%ile)"
            elif pct <= 90:
                cot_score = -0.7
                cot_label = f"❌ COT Very Long → Contrarian Bearish ({pct:.0f}%ile)"
            else:
                cot_score = -1.0
                cot_label = f"❌ COT Extreme Long → Contrarian Bearish ({pct:.0f}%ile)"

    component_scores["cot"] = cot_score
    component_details["cot"] = cot_label
    reasons.append(cot_label)

    # 4. Yield Curve (15%)
    yc_raw, yc_details = get_yield_curve_score(currency)
    yc_label = list(yc_details.values())[0] if yc_details else "N/A"
    yc_norm = max(-1.0, min(1.0, yc_raw / 25.0))
    component_scores["yield"] = yc_norm
    component_details["yield"] = yc_label
    reasons.append(f"{'✅' if yc_norm > 0.3 else '❌' if yc_norm < -0.3 else '⚪'} {yc_label}")

    # 5. Seasonality (5%)
    seas_score, seas_signal, _, _ = get_seasonal_score(currency)
    seas_norm = max(-1.0, min(1.0, seas_score / 7.0))
    seas_label = f"{'✅' if seas_norm > 0.3 else '❌' if seas_norm < -0.3 else '⚪'} {seas_signal}"
    component_scores["seasonality"] = seas_norm
    component_details["seasonality"] = seas_label
    reasons.append(seas_label)

    # 6. Political Risk (warning filter only)
    pol_score, _ = get_political_risk_score(currency)
    pol_warning = None
    if pol_score <= -20:
        pol_warning = f"⚠️ Political Risk High ({pol_score})"
        reasons.append(pol_warning)
    elif pol_score <= -10:
        pol_warning = f"🟠 Political Risk Elevated ({pol_score})"
        reasons.append(pol_warning)

    # Conflict Detection
    if component_scores["cb"] > 0.3 and component_scores["cot"] < -0.5:
        conflicts.append("⚠️ CB Bullish but COT Crowded Long")
    if component_scores["cb"] < -0.3 and component_scores["cot"] > 0.5:
        conflicts.append("⚠️ CB Bearish but COT Contrarian Bullish")
    if pol_warning:
        conflicts.append(pol_warning)

    # Weighted Net Score
    bullish_score = 0.0
    bearish_score = 0.0
    for key, weight in WEIGHTS.items():
        if key == "event":
            continue
        raw = component_scores.get(key, 0.0)
        contribution = raw * weight * 100
        if contribution > 0:
            bullish_score += contribution
        else:
            bearish_score += abs(contribution)

    net_score = bullish_score - bearish_score

    # Confidence
    total_weight = sum(v for k, v in WEIGHTS.items() if k != "event")
    weighted_abs = sum(abs(component_scores.get(k, 0.0)) * v for k, v in WEIGHTS.items() if k != "event")
    raw_confidence = (weighted_abs / total_weight) * 100
    confidence = max(0, min(100, round(raw_confidence - len(conflicts) * 15)))

    # Direction & Strength
    strength = _strength_label(net_score)
    if conflicts and abs(net_score) < 40:
        direction = "MIXED"
    elif net_score >= 15:
        direction = "BULLISH"
    elif net_score <= -15:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    signal_category = _signal_category(direction, strength, conflicts)

    biggest_edge = max(component_scores.items(), key=lambda x: abs(x[1]) * WEIGHTS.get(x[0], 0))
    biggest_edge_label = f"{component_details.get(biggest_edge[0], biggest_edge[0])} (weight: {int(WEIGHTS.get(biggest_edge[0], 0)*100)}%)"

    explanation = _build_explanation(currency, direction, component_details, conflicts, strength)

    return {
        "currency": currency,
        "direction": direction,
        "strength": strength,
        "signal_category": signal_category,
        "bullish_score": round(bullish_score, 1),
        "bearish_score": round(bearish_score, 1),
        "net_score": round(net_score, 1),
        "confidence": confidence,
        "conflicts": conflicts,
        "biggest_edge": biggest_edge_label,
        "explanation": explanation,
        "reasons": reasons,
        "bullish_count": round(bullish_score / 10),
        "bearish_count": round(bearish_score / 10),
        "total": 10,
    }

def get_best_confluences():
    results = [get_confluence_score(c) for c in CURRENCIES]
    bullish = [r for r in results if r["direction"] == "BULLISH" and r["strength"] in ("Strong", "Very Strong") and not r["conflicts"]]
    bearish = [r for r in results if r["direction"] == "BEARISH" and r["strength"] in ("Strong", "Very Strong") and not r["conflicts"]]
    setups = []
    for b in bullish:
        for s in bearish:
            trade = get_trade_direction(b["currency"], s["currency"])
            pair_confidence = round((b["confidence"] + s["confidence"]) / 2)
            setups.append({
                "trade": trade,
                "long": b["currency"],
                "short": s["currency"],
                "long_strength": b["strength"],
                "short_strength": s["strength"],
                "long_net_score": b["net_score"],
                "short_net_score": s["net_score"],
                "pair_confidence": pair_confidence,
                "long_reasons": b["reasons"],
                "short_reasons": s["reasons"],
                "long_explanation": b["explanation"],
                "short_explanation": s["explanation"],
                "confluence": b["net_score"] + abs(s["net_score"]),
            })
    return sorted(setups, key=lambda x: x["confluence"], reverse=True)

def get_currency_ranking():
    results = [get_confluence_score(c) for c in CURRENCIES]
    return sorted(results, key=lambda x: x["net_score"], reverse=True)


def _pair_signal(score):
    if score >= 50:
        return "✅ Strong Long"
    elif score >= 25:
        return "🟡 Long"
    elif score <= -50:
        return "🔴 Strong Short"
    elif score <= -25:
        return "🟠 Short"
    else:
        return "⚪ Neutral"

def get_pair_ranking():
    currency_scores = {c: get_confluence_score(c) for c in CURRENCIES}
    pairs = []
    seen = set()
    for a in CURRENCIES:
        for b in CURRENCIES:
            if a == b:
                continue
            key = tuple(sorted([a, b]))
            if key in seen:
                continue
            seen.add(key)
            score_a = currency_scores[a]["net_score"]
            score_b = currency_scores[b]["net_score"]
            pair_score = score_a - score_b
            if abs(pair_score) < 20:
                continue
            if pair_score > 0:
                base, quote = a, b
                direction = "LONG"
            else:
                base, quote = b, a
                direction = "SHORT"
                pair_score = abs(pair_score)
            trade = get_trade_direction(base, quote)
            confluence = min(100, round(abs(pair_score) * 1.2))
            signal = _pair_signal(pair_score if direction == "LONG" else -pair_score)
            pairs.append({
                "Pair": trade,
                "Base": base,
                "Quote": quote,
                "Direction": direction,
                "Pair Score": round(pair_score, 1),
                "Signal": signal,
                "Confluence": confluence,
                "Base Score": currency_scores[base]["net_score"],
                "Quote Score": currency_scores[quote]["net_score"],
                "Base Strength": currency_scores[base]["strength"],
                "Quote Strength": currency_scores[quote]["strength"],
                "Base Conflicts": currency_scores[base].get("conflicts", []),
                "Quote Conflicts": currency_scores[quote].get("conflicts", []),
            })
    return sorted(pairs, key=lambda x: x["Pair Score"], reverse=True)
