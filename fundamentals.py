import requests
import streamlit as st
from config import FRED_KEY

FRED_SERIES = {
    "USD": {
        "rate":         "FEDFUNDS",
        "cpi":          "CPIAUCSL",
        "core_cpi":     "CPILFESL",
        "ppi":          "PPIACO",
        "gdp":          "GDP",
        "unemployment": "UNRATE",
        "trade":        "BOPGSTB",
        "retail":       "RSAFS",
        "pmi_mfg":      "MANEMP",
        "debt_gdp":     "GFDEGDQ188S",
    },
    "EUR": {
        "rate":         "ECBDFR",
        "cpi":          "CP0000EZ19M086NEST",
        "core_cpi":     "CPGRLE01EZM659N",
        "ppi":          "PPIACZ01EZM661N",
        "gdp":          "EURGDPNQDSMEI",
        "unemployment": "LRHUTTTTEZM156S",
        "trade":        "XTEXVA01EZM667S",
        "retail":       "SLRTTO02EZM657S",
        "pmi_mfg":      "PRMNTO01EZM659S",
        "debt_gdp":     "DEUGGDTAQDSNALQ",
    },
    "GBP": {
        "rate":         "BOEBCPD",
        "cpi":          "GBRCPIALLMINMEI",
        "core_cpi":     "CPGRLE01GBM659N",
        "ppi":          "PPIACZ01GBM661N",
        "gdp":          "UKNGDP",
        "unemployment": "LRHUTTTTGBM156S",
        "trade":        "XTEXVA01GBM667S",
        "retail":       "SLRTTO02GBM657S",
        "pmi_mfg":      "PRMNTO01GBM659S",
        "debt_gdp":     "GBRGGDTAQDSNALQ",
    },
    "JPY": {
        "rate":         "IRSTJPN",
        "cpi":          "JPNCPIALLMINMEI",
        "core_cpi":     "CPGRLE01JPM659N",
        "ppi":          "PPIACZ01JPM661N",
        "gdp":          "JPNNGDP",
        "unemployment": "LRHUTTTTJPM156S",
        "trade":        "XTEXVA01JPM667S",
        "retail":       "SLRTTO02JPM657S",
        "pmi_mfg":      "PRMNTO01JPM659S",
        "debt_gdp":     "JPNGGDTAQDSNALQ",
    },
    "CHF": {
        "rate":         "IRSTCHF",
        "cpi":          "CHECPIALLMINMEI",
        "core_cpi":     "CPGRLE01CHM659N",
        "ppi":          "PPIACZ01CHM661N",
        "gdp":          "CHENGDPNQDSMEI",
        "unemployment": "LRHUTTTTCHM156S",
        "trade":        "XTEXVA01CHM667S",
        "retail":       "SLRTTO02CHM657S",
        "pmi_mfg":      "PRMNTO01CHM659S",
        "debt_gdp":     "CHEGGDTAQDSNALQ",
    },
    "AUD": {
        "rate":         "IRSTAUD",
        "cpi":          "AUSCPIALLMINMEI",
        "core_cpi":     "CPGRLE01AUM659N",
        "ppi":          "PPIACZ01AUM661N",
        "gdp":          "AUSGDPNQDSMEI",
        "unemployment": "LRHUTTTTAUM156S",
        "trade":        "XTEXVA01AUM667S",
        "retail":       "SLRTTO02AUM657S",
        "pmi_mfg":      "PRMNTO01AUM659S",
        "debt_gdp":     "AUSGGDTAQDSNALQ",
    },
    "CAD": {
        "rate":         "IRSTCAD",
        "cpi":          "CANCPIALLMINMEI",
        "core_cpi":     "CPGRLE01CAM659N",
        "ppi":          "PPIACZ01CAM661N",
        "gdp":          "CANGDPNQDSMEI",
        "unemployment": "LRHUTTTTCAM156S",
        "trade":        "XTEXVA01CAM667S",
        "retail":       "SLRTTO02CAM657S",
        "pmi_mfg":      "PRMNTO01CAM659S",
        "debt_gdp":     "CANGGDTAQDSNALQ",
    },
    "NZD": {
        "rate":         "IRSTNZD",
        "cpi":          "NZLCPIALLMINMEI",
        "core_cpi":     "CPGRLE01NZM659N",
        "ppi":          "PPIACZ01NZM661N",
        "gdp":          "NZLNGDPNQDSMEI",
        "unemployment": "LRHUTTTTCZM156S",
        "trade":        "XTEXVA01NZM667S",
        "retail":       "SLRTTO02NZM657S",
        "pmi_mfg":      "PRMNTO01NZM659S",
        "debt_gdp":     "NZLGGDTAQDSNALQ",
    },
}


@st.cache_data(ttl=86400)
def get_fred_series(series_id):
    url = (
        f"https://api.stlouisfed.org/fred/series/observations"
        f"?series_id={series_id}&api_key={FRED_KEY}"
        f"&file_type=json&sort_order=desc&limit=4"
    )
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
        if "observations" in data:
            return [float(o["value"]) for o in data["observations"] if o["value"] != "."]
    except:
        pass
    return []


def get_fundamental_score(currency):
    series = FRED_SERIES.get(currency, {})
    signals = []
    details = {}

    # 1. Interest Rate Momentum
    rate = get_fred_series(series.get("rate", ""))
    if len(rate) >= 2:
        if rate[0] > rate[1]:
            signals.append(1)
            details["Rate"] = f"✅ Rising ({rate[0]:.2f}%)"
        elif rate[0] < rate[1]:
            signals.append(-1)
            details["Rate"] = f"❌ Falling ({rate[0]:.2f}%)"
        else:
            signals.append(0)
            details["Rate"] = f"⚪ Unchanged ({rate[0]:.2f}%)"

    # 2. Rate Level
    if rate:
        if rate[0] > 3:
            signals.append(1)
            details["Rate Level"] = f"✅ High ({rate[0]:.2f}%)"
        elif rate[0] < 0.5:
            signals.append(-1)
            details["Rate Level"] = f"❌ Very Low ({rate[0]:.2f}%)"
        else:
            signals.append(0)
            details["Rate Level"] = f"⚪ Neutral ({rate[0]:.2f}%)"

    # 3. CPI Momentum
    cpi = get_fred_series(series.get("cpi", ""))
    if len(cpi) >= 2:
        mom = ((cpi[0] - cpi[1]) / abs(cpi[1])) * 100 if cpi[1] != 0 else 0
        if mom > 0.1:
            signals.append(0.5)
            details["CPI"] = f"🟡 Rising ({mom:+.2f}%)"
        elif mom < -0.1:
            signals.append(-0.5)
            details["CPI"] = f"🟠 Falling ({mom:+.2f}%)"
        else:
            signals.append(0)
            details["CPI"] = f"⚪ Stable"

    # 4. Core CPI
    core = get_fred_series(series.get("core_cpi", ""))
    if len(core) >= 2:
        mom = ((core[0] - core[1]) / abs(core[1])) * 100 if core[1] != 0 else 0
        if mom > 0.1:
            signals.append(0.5)
            details["Core CPI"] = f"🟡 Rising ({mom:+.2f}%)"
        elif mom < -0.1:
            signals.append(-0.5)
            details["Core CPI"] = f"🟠 Falling ({mom:+.2f}%)"
        else:
            signals.append(0)
            details["Core CPI"] = f"⚪ Stable"

    # 5. PPI
    ppi = get_fred_series(series.get("ppi", ""))
    if len(ppi) >= 2:
        if ppi[0] > ppi[1]:
            signals.append(0.5)
            details["PPI"] = f"✅ Rising"
        else:
            signals.append(-0.5)
            details["PPI"] = f"❌ Falling"

    # 6. GDP
    gdp = get_fred_series(series.get("gdp", ""))
    if len(gdp) >= 2:
        if gdp[0] > gdp[1]:
            signals.append(1)
            details["GDP"] = f"✅ Growing"
        else:
            signals.append(-1)
            details["GDP"] = f"❌ Shrinking"

    # 7. Unemployment
    unemp = get_fred_series(series.get("unemployment", ""))
    if len(unemp) >= 2:
        if unemp[0] < unemp[1]:
            signals.append(1)
            details["Unemployment"] = f"✅ Falling ({unemp[0]:.1f}%)"
        else:
            signals.append(-1)
            details["Unemployment"] = f"❌ Rising ({unemp[0]:.1f}%)"

    # 8. Retail Sales
    retail = get_fred_series(series.get("retail", ""))
    if len(retail) >= 2:
        if retail[0] > retail[1]:
            signals.append(1)
            details["Retail Sales"] = f"✅ Growing"
        else:
            signals.append(-1)
            details["Retail Sales"] = f"❌ Falling"

    # 9. PMI Manufacturing
    pmi = get_fred_series(series.get("pmi_mfg", ""))
    if len(pmi) >= 2:
        if pmi[0] > 50:
            signals.append(1)
            details["PMI Mfg"] = f"✅ Expansion ({pmi[0]:.1f})"
        else:
            signals.append(-1)
            details["PMI Mfg"] = f"❌ Contraction ({pmi[0]:.1f})"

    # 10. Debt-to-GDP
    debt = get_fred_series(series.get("debt_gdp", ""))
    if len(debt) >= 2:
        if debt[0] < debt[1]:
            signals.append(0.5)
            details["Debt/GDP"] = f"✅ Falling ({debt[0]:.1f}%)"
        else:
            signals.append(-0.5)
            details["Debt/GDP"] = f"🟠 Rising ({debt[0]:.1f}%)"

    bullish = sum(1 for s in signals if s > 0)
    bearish = sum(1 for s in signals if s < 0)
    total = len(signals)
    score = sum(signals)

    return {
        "score":   round(score, 1),
        "bullish": bullish,
        "bearish": bearish,
        "total":   total,
        "details": details,
    }
