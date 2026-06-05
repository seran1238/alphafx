import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from config import CURRENCIES
from calendar_data import get_central_bank_bias, get_upcoming_events
from rate_differential import get_all_differentials, get_hawkish_dovish_ranking
from cot_extremes import get_cot_percentile, load_historical_cot
from confluence import get_confluence_score, get_best_confluences, get_currency_ranking, get_pair_ranking
from forex_pairs import get_trade_direction
from yield_curve import get_yield_curve_score, get_all_yield_curves
from seasonality import get_seasonal_score, get_all_seasonality
from political_risk import get_political_risk_score, get_political_risk_label

st.set_page_config(page_title="AlphaFX", layout="wide", page_icon="📡")

flags = {"USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","JPY":"🇯🇵","CHF":"🇨🇭","AUD":"🇦🇺","CAD":"🇨🇦","NZD":"🇳🇿"}

col1, col2 = st.columns([3,1])
with col1:
    st.title("📡 AlphaFX — Institutional Currency Analysis")
    st.caption("Macro · COT Extremes · Rate Differentials · Yield Curve · Seasonality · Dalio Regime · Confluence")
with col2:
    st.markdown(f"**{datetime.now().strftime('%d.%m.%Y %H:%M')}**")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

try:
    from macro import get_macro_score
    from config import FRED_KEY
    import requests
    gdp_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=A191RL1Q225SBEA&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=2"
    cpi_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key={FRED_KEY}&file_type=json&sort_order=desc&limit=2"
    gdp_data = requests.get(gdp_url, timeout=5).json().get("observations", [])
    cpi_data = requests.get(cpi_url, timeout=5).json().get("observations", [])
    gdp_val = float(gdp_data[0]["value"]) if gdp_data else 0
    cpi_val = float(cpi_data[0]["value"]) if cpi_data and cpi_data[0]["value"] != "." else 0
    cpi_prev = float(cpi_data[1]["value"]) if len(cpi_data) > 1 and cpi_data[1]["value"] != "." else cpi_val
    inflation_mom = ((cpi_val - cpi_prev) / cpi_prev) * 100 if cpi_prev else 0
    if gdp_val > 0 and inflation_mom > 0:
        regime = "🔥 Reflation"
        regime_desc = "Growth↑ Inflation↑ — Commodity FX (AUD/CAD/NZD)"
    elif gdp_val > 0 and inflation_mom <= 0:
        regime = "🌟 Goldilocks"
        regime_desc = "Growth↑ Inflation↓ — Risk-On, equities bullish"
    elif gdp_val <= 0 and inflation_mom > 0:
        regime = "⚠️ Stagflation"
        regime_desc = "Growth↓ Inflation↑ — Gold, JPY, CHF"
    else:
        regime = "Deflation/Recession"
        regime_desc = "Growth↓ Inflation↓ — JPY, USD, Bonds"
    st.info(f"**{regime}** — {regime_desc} | Growth: {gdp_val:+.2f}% | Inflation MoM: {inflation_mom:+.2f}%")
except:
    pass

def conf_color(c):
    if c >= 90: return "🟢🟢"
    elif c >= 70: return "🟢"
    elif c >= 50: return "🟡"
    else: return "⚫"


def trade_quality(confluence, abs_score):
    if confluence >= 90 and abs_score >= 70:
        return "A+"
    elif confluence >= 75 and abs_score >= 55:
        return "A"
    elif confluence >= 60 and abs_score >= 40:
        return "B+"
    elif confluence >= 50 and abs_score >= 25:
        return "B"
    else:
        return "C"

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "🔥 Pair Dashboard",
    "🎯 Confluence",
    "🏦 COT Extremes",
    "🌍 Macro & Rates",
    "📈 Yield Curve & Seasonality",
    "📅 Event Calendar",
    "🗞️ Political Risk",
    "📊 Economic Regime"
])

with tab1:
    st.subheader("🔥 Pair Score Ranking")
    st.caption("Pair Score = Currency A Net Score − Currency B Net Score. Higher = stronger divergence.")

    with st.spinner("Calculating pair scores..."):
        pairs = get_pair_ranking()
        all_confluence = [get_confluence_score(c) for c in CURRENCIES]

    if pairs:
        # Elite Setups
        elite = [p for p in pairs if p["Confluence %"] >= 70 and abs(p["Pair Score"]) >= 50]
        if elite:
            st.markdown("### 🏆 Elite Setups")
            st.caption("Confluence >= 70% and |Pair Score| >= 50")
            for p in elite:
                direction_label = "Short" if p["Pair Score"] < 0 else "Long"
                quality = trade_quality(p["Confluence %"], abs(p["Pair Score"]))
                st.success(
                    f"**{p['Pair']}** {direction_label} | "
                    f"Score: `{p['Pair Score']:+.1f}` | "
                    f"Confluence: {conf_color(p['Confluence %'])} `{p['Confluence %']}%` | "
                    f"Rating: **{quality}** | "
                    f"Final Score: `{p['Final Score']}`"
                )
            st.markdown("---")

        quality_pairs = [p for p in pairs if p["Confluence %"] >= 50]
        top_longs = [p for p in quality_pairs if p["Pair Score"] > 0][:5]
        top_shorts = [p for p in quality_pairs if p["Pair Score"] < 0][:5]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 Top Longs")
            if top_longs:
                for p in top_longs:
                    st.markdown(
                        f"**{flags.get(p['Base'],'')} {p['Pair']}** | "
                        f"Score: `{p['Pair Score']:+.1f}` | "
                        f"{conf_color(p['Confluence %'])} `{p['Confluence %']}%` | {p['Signal']}"
                    )
            else:
                st.info("No quality long setups (Confluence < 50%)")

        with col2:
            st.markdown("### 📉 Top Shorts")
            if top_shorts:
                for p in top_shorts:
                    quality = trade_quality(p["Confluence %"], abs(p["Pair Score"]))
                    st.markdown(
                        f"**{flags.get(p['Base'],'')} {p['Pair']}** | "
                        f"Score: `{p['Pair Score']:+.1f}` | "
                        f"{conf_color(p['Confluence %'])} `{p['Confluence %']}%` | "
                        f"**{quality}** | {p['Signal']}"
                    )
            else:
                st.info("No quality short setups (Confluence < 50%)")

        st.markdown("---")
        st.subheader("📋 Signal Explanations")
        for p in [p for p in pairs if p["Confluence %"] >= 50][:6]:
            direction_label = "Short" if p["Pair Score"] < 0 else "Long"
            quality = trade_quality(p["Confluence %"], abs(p["Pair Score"]))
            quality_color = "🟢" if quality in ("A+","A") else "🟡" if quality == "B+" else "🟠"
            with st.expander(
                f"**{p['Pair']}** {direction_label} | "
                f"Score: `{p['Pair Score']:+.1f}` | "
                f"{conf_color(p['Confluence %'])} `{p['Confluence %']}%` | "
                f"Rating: {quality_color} **{quality}**",
                expanded=True
            ):
                col1, col2 = st.columns(2)
                with col1:
                    base_label = "Bearish" if p["Pair Score"] < 0 else "Bullish"
                    st.markdown(f"**{flags.get(p['Base'],'')} {p['Base']} — {base_label} ({p['Base Score']:+.1f})**")
                    for r in p.get("Base Reasons", [])[:7]:
                        st.markdown(f"  {r}")
                    if p.get("Base Conflicts"):
                        for c in p["Base Conflicts"]:
                            st.warning(c)
                with col2:
                    quote_label = "Bullish" if p["Pair Score"] < 0 else "Bearish"
                    st.markdown(f"**{flags.get(p['Quote'],'')} {p['Quote']} — {quote_label} ({p['Quote Score']:+.1f})**")
                    for r in p.get("Quote Reasons", [])[:7]:
                        st.markdown(f"  {r}")
                    if p.get("Quote Conflicts"):
                        for c in p["Quote Conflicts"]:
                            st.warning(c)

        st.subheader("📊 All Pairs Ranked")
        pair_table = []
        for p in pairs:
            pair_table.append({
                "Pair": p["Pair"],
                "Direction": p["Direction"],
                "Pair Score": p["Pair Score"],
                "Signal": p["Signal"],
                "Confluence %": p["Confluence %"],
                "Base Score": p["Base Score"],
                "Quote Score": p["Quote Score"],
                "Conflicts": "⚠️" if p["Base Conflicts"] or p["Quote Conflicts"] else "✅"
            })
        df_pairs = pd.DataFrame(pair_table).sort_values("Pair Score", ascending=False)
        st.dataframe(df_pairs, use_container_width=True, hide_index=True)

        st.subheader("📊 Pair Score Bar Chart")
        fig_pairs = go.Figure()
        for p in pair_table:
            score = p["Pair Score"]
            color = "#2ecc71" if score > 25 else "#e74c3c" if score < -25 else "#e67e22"
            fig_pairs.add_trace(go.Bar(
                x=[p["Pair"]],
                y=[score],
                marker_color=color,
                name=p["Pair"],
                text=f"{score:+.0f}",
                textposition="outside"
            ))
        fig_pairs.update_layout(
            title="Pair Score Ranking",
            showlegend=False,
            plot_bgcolor="#1e1e2e",
            paper_bgcolor="#1e1e2e",
            font_color="white",
            height=400
        )
        st.plotly_chart(fig_pairs, use_container_width=True)
    else:
        st.info("No significant pair divergences found at this time.")

with tab2:
    st.subheader("🎯 High Confluence Trade Setups")
    st.caption("Only shows setups where macro, rates, COT, yield curve AND regime all align")
    with st.spinner("Calculating confluence..."):
        setups = get_best_confluences()
        if not 'all_confluence' in dir():
            all_confluence = [get_confluence_score(c) for c in CURRENCIES]
    if setups:
        for setup in setups[:3]:
            conf_pct = setup.get("pair_confidence", 0)
            label = f"**{setup['trade']}** — Long {setup['long_strength']} | Short {setup['short_strength']} | Confidence: {conf_pct}%"
            with st.expander(label, expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{flags.get(setup['long'],'')} {setup['long']} — LONG** | Net Score: `{setup.get('long_net_score', '')}`")
                    st.code(setup.get("long_explanation", ""), language=None)
                with col2:
                    st.markdown(f"**{flags.get(setup['short'],'')} {setup['short']} — SHORT** | Net Score: `{setup.get('short_net_score', '')}`")
                    st.code(setup.get("short_explanation", ""), language=None)
    else:
        st.warning("No strong confluence setups at this time. Markets may be mixed.")

    st.subheader("Currency Confluence Overview")
    conf_data = []
    for r in all_confluence:
        c = r["currency"]
        net = r.get("net_score", 0)
        conf_data.append({
            "Currency": f"{flags.get(c,'')} {c}",
            "Direction": r["direction"],
            "Strength": r["strength"],
            "Signal": r.get("signal_category", ""),
            "Net Score": net,
            "Bullish": r.get("bullish_score", r["bullish_count"]),
            "Bearish": r.get("bearish_score", r["bearish_count"]),
            "Confidence %": r.get("confidence", "-"),
            "Factors": r["total"],
            "Reasons": " | ".join(r["reasons"])
        })
    df = pd.DataFrame(conf_data).sort_values("Net Score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("📊 Currency Strength Ranking")
    ranking_data = sorted(all_confluence, key=lambda x: x.get("net_score", 0), reverse=True)
    fig_rank = go.Figure()
    for r in ranking_data:
        c = r["currency"]
        net = r.get("net_score", 0)
        color = "#2ecc71" if net > 25 else "#e74c3c" if net < -25 else "#e67e22"
        fig_rank.add_trace(go.Bar(
            x=[f"{flags.get(c,'')} {c}"],
            y=[net],
            marker_color=color,
            name=c,
            text=f"{net:+.0f}",
            textposition="outside"
        ))
    fig_rank.update_layout(
        title="Net Score per Currency (-100 to +100)",
        showlegend=False,
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="white",
        height=350,
        yaxis=dict(range=[-100, 100])
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    conflicts_found = [r for r in all_confluence if r.get("conflicts")]
    if conflicts_found:
        st.subheader("⚠️ Signal Conflicts")
        for r in conflicts_found:
            c = r["currency"]
            for conflict in r["conflicts"]:
                st.warning(f"{flags.get(c,'')} **{c}**: {conflict}")

    st.subheader("💡 Biggest Edge per Currency")
    for r in all_confluence:
        c = r["currency"]
        edge = r.get("biggest_edge", "")
        if edge:
            st.markdown(f"**{flags.get(c,'')} {c}:** {edge}")

with tab3:
    st.subheader("🏦 COT Positioning Extremes")
    st.caption("Extreme positioning = contrarian signal. 90%ile long = potential reversal down.")
    with st.spinner("Loading COT data..."):
        cot_data = []
        for c in CURRENCIES:
            if c == "USD":
                continue
            data = get_cot_percentile(c)
            if data:
                cot_data.append({
                    "Currency": f"{flags.get(c,'')} {c}",
                    "HF Net": f"{data['lm_net']:,.0f}",
                    "HF %ile": f"{data['lm_percentile']:.0f}%",
                    "HF Signal": data['lm_extreme'],
                    "AM Net": f"{data['am_net']:,.0f}",
                    "AM %ile": f"{data['am_percentile']:.0f}%",
                    "AM Signal": data['am_extreme'],
                })
    if cot_data:
        st.dataframe(pd.DataFrame(cot_data), use_container_width=True, hide_index=True)
    st.subheader("📊 Weekly Net Change & OI Confirmation")
    change_data = []
    for c in CURRENCIES:
        if c == "USD":
            continue
        data = get_cot_percentile(c)
        if data:
            change_data.append({
                "Currency": f"{flags.get(c,'')} {c}",
                "HF Net Change": f"{data['lm_change']:+,.0f}",
                "HF Momentum": data['lm_momentum'],
                "AM Net Change": f"{data['am_change']:+,.0f}",
                "Open Interest": f"{data['open_interest']:,.0f}",
                "OI Signal": data['oi_signal'],
            })
    if change_data:
        st.dataframe(pd.DataFrame(change_data), use_container_width=True, hide_index=True)
    st.subheader("COT History Chart")
    selected = st.selectbox("Select Currency", [c for c in CURRENCIES if c != "USD"])
    cot_detail = get_cot_percentile(selected)
    if cot_detail and cot_detail.get("history") is not None:
        hist = cot_detail["history"].tail(52)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=hist["date"],
            y=hist["lm_net"],
            name="Hedge Fund Net",
            marker_color=["#2ecc71" if v > 0 else "#e74c3c" for v in hist["lm_net"]]
        ))
        fig.add_trace(go.Scatter(
            x=hist["date"],
            y=hist["lm_change"].cumsum(),
            name="Cumulative Change",
            line=dict(color="#f39c12", width=2),
            yaxis="y2"
        ))
        fig.update_layout(
            title=f"{selected} — Hedge Fund Net Positioning (1 Year)",
            plot_bgcolor="#1e1e2e",
            paper_bgcolor="#1e1e2e",
            font_color="white",
            height=400,
            yaxis2=dict(overlaying="y", side="right", showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("🌍 Central Bank Bias & Rate Differentials")
    with st.spinner("Loading macro data..."):
        ranking = get_hawkish_dovish_ranking()
        differentials = get_all_differentials()
    st.markdown("**Central Bank Hawkish/Dovish Ranking**")
    cb_data = []
    for r in ranking:
        c = r["currency"]
        bias_emoji = "🟢" if r["bias"] == "Hawkish" else "🔴" if r["bias"] == "Dovish" else "🟡"
        trend_emoji = "📈" if r["trend"] == "Hiking" else "📉" if r["trend"] == "Cutting" else "➡️"
        cb_data.append({
            "Currency": f"{flags.get(c,'')} {c}",
            "Rate": f"{r['rate']}%",
            "Bias": f"{bias_emoji} {r['bias']}",
            "Trend": f"{trend_emoji} {r['trend']}",
            "Last Change": r["last_change"]
        })
    st.dataframe(pd.DataFrame(cb_data), use_container_width=True, hide_index=True)
    st.markdown("**Top Rate Differentials (Carry Trade)**")
    diff_df = pd.DataFrame(differentials[:10])
    diff_df["Favor"] = diff_df["Favor"].apply(lambda x: f"{flags.get(x,'')} {x}")
    st.dataframe(diff_df[["Pair","Rate 1","Rate 2","Differential","Favor","Attractiveness"]],
                 use_container_width=True, hide_index=True)
    fig2 = go.Figure()
    for r in ranking:
        c = r["currency"]
        color = "#2ecc71" if r["bias"] == "Hawkish" else "#e74c3c" if r["bias"] == "Dovish" else "#e67e22"
        fig2.add_trace(go.Bar(
            x=[f"{flags.get(c,'')} {c}"],
            y=[r["score"]],
            marker_color=color,
            name=c
        ))
    fig2.update_layout(
        title="Central Bank Hawkish/Dovish Score",
        showlegend=False,
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="white",
        height=300
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab5:
    st.subheader("📈 Yield Curve & Seasonality")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Yield Curve Analysis**")
        with st.spinner("Loading yield curves..."):
            yc_data = get_all_yield_curves()
        yc_display = []
        for r in yc_data:
            c = r["currency"]
            yc_display.append({
                "Currency": f"{flags.get(c,'')} {c}",
                "Yield Curve": r["yield_curve"],
                "Trend": r["trend"],
                "Score": r["score"]
            })
        st.dataframe(pd.DataFrame(yc_display).sort_values("Score", ascending=False),
                     use_container_width=True, hide_index=True)
    with col2:
        st.markdown(f"**Seasonal Patterns — {datetime.now().strftime('%B %Y')}**")
        seasonal = get_all_seasonality()
        seas_display = []
        for r in seasonal:
            c = r["currency"]
            seas_display.append({
                "Currency": f"{flags.get(c,'')} {c}",
                "Signal": r["signal"],
                "This Month": r["current_month"],
                "Next Month": r["next_month"],
                "Score": r["score"]
            })
        st.dataframe(pd.DataFrame(seas_display), use_container_width=True, hide_index=True)
    st.subheader("Seasonal Heatmap")
    import calendar as cal
    months = [cal.month_abbr[i] for i in range(1, 13)]
    from seasonality import SEASONAL_PATTERNS
    fig3 = go.Figure(data=go.Heatmap(
        z=[[SEASONAL_PATTERNS.get(c, {}).get(m, 0) for m in range(1, 13)] for c in CURRENCIES],
        x=months,
        y=[f"{flags.get(c,'')} {c}" for c in CURRENCIES],
        colorscale="RdYlGn",
        zmid=0
    ))
    fig3.update_layout(
        title="Currency Seasonal Patterns (Monthly Avg)",
        plot_bgcolor="#1e1e2e",
        paper_bgcolor="#1e1e2e",
        font_color="white",
        height=350
    )
    st.plotly_chart(fig3, use_container_width=True)

with tab6:
    st.subheader("📅 Upcoming High Impact Events")
    st.caption("Next 14 days — events that can move currency markets")
    with st.spinner("Loading calendar..."):
        all_events = []
        for c in CURRENCIES:
            events = get_upcoming_events(c)
            for e in events:
                e["currency"] = f"{flags.get(c,'')} {c}"
                all_events.append(e)
    if all_events:
        events_df = pd.DataFrame(all_events).sort_values("date")
        st.dataframe(events_df[["date","currency","event","impact","previous","estimate"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No upcoming high impact events found or API limit reached.")

with tab7:
    st.subheader("🗞️ Political Risk")
    st.caption("Only shown when risk is elevated — neutral signals are filtered out.")
    for c in CURRENCIES:
        pol_score, headlines = get_political_risk_score(c)
        if pol_score <= -10:
            label = get_political_risk_label(pol_score)
            st.warning(f"**{flags.get(c,'')} {c}** — {label} (score: {pol_score})")
            if headlines:
                for h in headlines[:3]:
                    st.markdown(f"  - {h}")

with tab8:
    st.subheader("📊 Economic Regime — Dalio Four Quadrants")
    st.caption("Based on Growth Momentum + Inflation Momentum from FRED data")
    regime_data = []
    for c in CURRENCIES:
        try:
            from macro import get_macro_score
            score, details = get_macro_score(c)
            regime_data.append({
                "Currency": f"{flags.get(c,'')} {c}",
                "Macro Score": score,
                "Details": " | ".join([f"{k}: {v}" for k, v in details.items()])
            })
        except:
            pass
    if regime_data:
        st.dataframe(
            pd.DataFrame(regime_data).sort_values("Macro Score", ascending=False),
            use_container_width=True,
            hide_index=True
        )

st.markdown("---")
st.caption(f"AlphaFX — Institutional Grade | Macro · COT · Rates · Yield Curve · Seasonality · GDELT Political Risk · Dalio Regime · Confluence | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
