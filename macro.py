import requests
from config import FRED_KEY

RATE_SERIES = {
    "USD": "FEDFUNDS",
    "EUR": "ECBDFR",
    "GBP": "BOEBCPD",
    "JPY": "IRSTJPN",
    "CHF": "IRSTCHF",
    "AUD": "IRSTAUD",
    "CAD": "IRSTCAD",
    "NZD": "IRSTNZD",
}

CPI_SERIES = {
    "USD": "CPIAUCSL",
    "EUR": "CP0000EZ19M086NEST",
    "GBP": "GBRCPIALLMINMEI",
    "JPY": "JPNCPIALLMINMEI",
    "CHF": "CHECPIALLMINMEI",
    "AUD": "AUSCPIALLMINMEI",
    "CAD": "CANCPIALLMINMEI",
    "NZD": "NZLCPIALLMINMEI",
}

CURRENT_ACCOUNT_SERIES = {
    "USD": "NETFI",
    "EUR": "BPBLTT01EZQ188S",
    "GBP": "BPBLTT01GBQ188S",
    "JPY": "BPBLTT01JPQ188S",
    "CHF": "BPBLTT01CHQ188S",
    "AUD": "BPBLTT01AUQ188S",
    "CAD": "BPBLTT01CAQ188S",
    "NZD": "BPBLTT01NZQ188S",
}

def get_fred(series_id, limit=4):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit={limit}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if "observations" in data:
            return [float(o["value"]) for o in data["observations"] if o["value"] != "."]
    except:
        pass
    return []

def get_real_interest_rate(currency):
    rate = get_fred(RATE_SERIES.get(currency, ""))
    cpi = get_fred(CPI_SERIES.get(currency, ""))
    if rate and cpi and len(cpi) >= 2:
        cpi_change = ((cpi[0] - cpi[1]) / cpi[1]) * 100 * 12
        real_rate = rate[0] - cpi_change
        return real_rate, rate[0], cpi_change
    return None, None, None

def get_macro_score(currency):
    score = 0
    details = {}

    # Real Interest Rate
    real_rate, nominal_rate, inflation = get_real_interest_rate(currency)
    if real_rate is not None:
        if real_rate > 2:
            score += 35
            details["Real Rate"] = f"+35 (High: {real_rate:.2f}%)"
        elif real_rate > 0:
            score += 20
            details["Real Rate"] = f"+20 (Positive: {real_rate:.2f}%)"
        elif real_rate > -1:
            score -= 10
            details["Real Rate"] = f"-10 (Slightly Negative: {real_rate:.2f}%)"
        else:
            score -= 30
            details["Real Rate"] = f"-30 (Very Negative: {real_rate:.2f}%)"

    # Current Account
    ca = get_fred(CURRENT_ACCOUNT_SERIES.get(currency, ""), limit=4)
    if len(ca) >= 2:
        if ca[0] > 0 and ca[0] > ca[1]:
            score += 25
            details["Current Account"] = f"+25 (Surplus & Improving)"
        elif ca[0] > 0:
            score += 15
            details["Current Account"] = f"+15 (Surplus)"
        elif ca[0] < 0 and ca[0] < ca[1]:
            score -= 25
            details["Current Account"] = f"-25 (Deficit & Worsening)"
        else:
            score -= 10
            details["Current Account"] = f"-10 (Deficit)"

    # Carry Trade attractiveness
    rate_data = get_fred(RATE_SERIES.get(currency, ""), limit=3)
    if rate_data:
        if rate_data[0] > 4:
            score += 20
            details["Carry"] = f"+20 (Very Attractive: {rate_data[0]:.2f}%)"
        elif rate_data[0] > 2:
            score += 10
            details["Carry"] = f"+10 (Attractive: {rate_data[0]:.2f}%)"
        elif rate_data[0] < 0.5:
            score -= 20
            details["Carry"] = f"-20 (Unattractive: {rate_data[0]:.2f}%)"

    return score, details
