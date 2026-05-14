import requests
from config import FRED_KEY

FRED_SERIES = {
    "USD": {
        "rate": "FEDFUNDS",
        "cpi": "CPIAUCSL",
        "gdp": "GDP",
        "unemployment": "UNRATE",
        "trade": "BOPGSTB"
    },
    "EUR": {
        "rate": "ECBDFR",
        "cpi": "CP0000EZ19M086NEST",
        "gdp": "EURGDPNQDSMEI",
        "unemployment": "LRHUTTTTEZM156S",
        "trade": "XTEXVA01EZM667S"
    },
    "GBP": {
        "rate": "BOEBCPD",
        "cpi": "GBRCPIALLMINMEI",
        "gdp": "UKNGDP",
        "unemployment": "LRHUTTTTGBM156S",
        "trade": "XTEXVA01GBM667S"
    },
    "JPY": {
        "rate": "IRSTJPN",
        "cpi": "JPNCPIALLMINMEI",
        "gdp": "JPNNGDP",
        "unemployment": "LRHUTTTTJPM156S",
        "trade": "XTEXVA01JPM667S"
    },
    "CHF": {
        "rate": "IRSTCHF",
        "cpi": "CHECPIALLMINMEI",
        "gdp": "CHENGDPNQDSMEI",
        "unemployment": "LRHUTTTTCHM156S",
        "trade": "XTEXVA01CHM667S"
    },
    "AUD": {
        "rate": "IRSTAUD",
        "cpi": "AUSCPIALLMINMEI",
        "gdp": "AUSGDPNQDSMEI",
        "unemployment": "LRHUTTTTAUM156S",
        "trade": "XTEXVA01AUM667S"
    },
    "CAD": {
        "rate": "IRSTCAD",
        "cpi": "CANCPIALLMINMEI",
        "gdp": "CANGDPNQDSMEI",
        "unemployment": "LRHUTTTTCAM156S",
        "trade": "XTEXVA01CAM667S"
    },
    "NZD": {
        "rate": "IRSTNZD",
        "cpi": "NZLCPIALLMINMEI",
        "gdp": "NZLNGDPNQDSMEI",
        "unemployment": "LRHUTTTTCZM156S",
        "trade": "XTEXVA01NZM667S"
    },
}

def get_fred_series(series_id):
    url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=3"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if "observations" in data:
            vals = [float(o["value"]) for o in data["observations"] if o["value"] != "."]
            return vals
    except:
        pass
    return []

def get_fundamental_score(currency):
    series = FRED_SERIES.get(currency, {})
    score = 0
    details = {}

    # Interest Rate — most important
    rate_data = get_fred_series(series.get("rate", ""))
    if len(rate_data) >= 2:
        if rate_data[0] > rate_data[1]:
            score += 30
            details["Rate"] = "+30 (Rising)"
        elif rate_data[0] < rate_data[1]:
            score -= 30
            details["Rate"] = "-30 (Falling)"
        else:
            details["Rate"] = "0 (Unchanged)"
        if rate_data[0] > 3:
            score += 10
            details["Rate Level"] = "+10 (High)"
        elif rate_data[0] < 1:
            score -= 10
            details["Rate Level"] = "-10 (Low)"

    # CPI Inflation
    cpi_data = get_fred_series(series.get("cpi", ""))
    if len(cpi_data) >= 2:
        if cpi_data[0] > cpi_data[1]:
            score += 10
            details["CPI"] = "+10 (Rising)"
        else:
            score -= 5
            details["CPI"] = "-5 (Falling)"

    # GDP Growth
    gdp_data = get_fred_series(series.get("gdp", ""))
    if len(gdp_data) >= 2:
        if gdp_data[0] > gdp_data[1]:
            score += 20
            details["GDP"] = "+20 (Growing)"
        else:
            score -= 15
            details["GDP"] = "-15 (Shrinking)"

    # Unemployment
    unemp_data = get_fred_series(series.get("unemployment", ""))
    if len(unemp_data) >= 2:
        if unemp_data[0] < unemp_data[1]:
            score += 15
            details["Unemployment"] = "+15 (Falling)"
        else:
            score -= 10
            details["Unemployment"] = "-10 (Rising)"

    # Trade Balance
    trade_data = get_fred_series(series.get("trade", ""))
    if len(trade_data) >= 2:
        if trade_data[0] > trade_data[1]:
            score += 10
            details["Trade"] = "+10 (Improving)"
        else:
            score -= 5
            details["Trade"] = "-5 (Worsening)"

    return score, details
