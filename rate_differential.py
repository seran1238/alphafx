from calendar_data import get_central_bank_bias
from config import CURRENCIES

def get_rate_differential(currency1, currency2):
    bias1 = get_central_bank_bias(currency1)
    bias2 = get_central_bank_bias(currency2)
    diff = bias1["rate"] - bias2["rate"]
    return round(diff, 2)

def get_carry_attractiveness(currency1, currency2):
    diff = get_rate_differential(currency1, currency2)
    if diff > 3:
        return "🟢 Very Attractive", diff
    elif diff > 1.5:
        return "🟡 Attractive", diff
    elif diff > 0:
        return "⚪ Slight", diff
    elif diff > -1.5:
        return "⚪ Slight (Inverse)", diff
    elif diff > -3:
        return "🟡 Attractive (Inverse)", diff
    else:
        return "🟢 Very Attractive (Inverse)", diff

def get_all_differentials():
    pairs = []
    for i, c1 in enumerate(CURRENCIES):
        for c2 in CURRENCIES[i+1:]:
            label, diff = get_carry_attractiveness(c1, c2)
            b1 = get_central_bank_bias(c1)
            b2 = get_central_bank_bias(c2)
            pairs.append({
                "Pair": f"{c1}/{c2}",
                "Rate 1": b1["rate"],
                "Rate 2": b2["rate"],
                "Differential": abs(diff),
                "Favor": c1 if diff > 0 else c2,
                "Attractiveness": label,
                "Trend 1": b1["trend"],
                "Trend 2": b2["trend"],
            })
    return sorted(pairs, key=lambda x: x["Differential"], reverse=True)

def get_hawkish_dovish_ranking():
    ranking = []
    for c in CURRENCIES:
        bias = get_central_bank_bias(c)
        score = 0
        if bias["trend"] == "Hiking":
            score += 30
        elif bias["trend"] == "Cutting":
            score -= 30
        if bias["bias"] == "Hawkish":
            score += 20
        elif bias["bias"] == "Dovish":
            score -= 20
        score += bias["rate"] * 2
        ranking.append({
            "currency": c,
            "score": score,
            "bias": bias["bias"],
            "rate": bias["rate"],
            "trend": bias["trend"],
            "last_change": bias["last_change"]
        })
    return sorted(ranking, key=lambda x: x["score"], reverse=True)
