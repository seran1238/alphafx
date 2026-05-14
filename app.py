import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from config import CURRENCIES
from calendar_data import get_central_bank_bias, get_upcoming_events
from rate_differential import get_all_differentials, get_hawkish_dovish_ranking
from cot_extremes import get_cot_percentile, load_historical_cot
from confluence import get_confluence_score, get_best_confluences
from forex_pairs import get_trade_direction
from yield_curve import get_yield_curve_score, get_all_yield_curves
from seasonality import get_seasonal_score, get_all_seasonality

st.set_page_config(page_title="AlphaFX", layout="wide", page_icon="📡")

flags = {"USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","JPY":"🇯🇵","CHF":"🇨🇭","AUD":"🇦🇺","CAD":"🇨🇦","NZD":"🇳🇿"}

col1, col2 = st.columns([3,1])
with col1:
    st.title("📡 AlphaFX — Institutional Currency Analysis")
    st.caption("Macro · COT Extremes · Rate Differentials · Yield Curve · Seasonality · Confluence")
with col2:
    st.markdown(f"**{datetime.now().strftime('%d.%m.%Y %H:%M')}**")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Confluence",
    "🏦 COT Extremes",
    "🌍 Macro & Rates",
    "📈 Yield Curve & Seasonality",
    "📅 Event Calendar"
])

with tab1:
    st.subheader("🎯 High Confluence Trade Setups")
    st.caption("Only shows setups where macro, rates, COT AND yield curve all align")

    with st.spinner("Calculating confluence..."):
        setups = get_best_confluences()
        all_confluence = [get_confluence_score(c) for c in CURRENCIES]

    if setups:
        for setup in setups[:3]:
            with st.expander(f"**{setup['trade']}** — {setup['long_strength']}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{flags.get(setup['long'],'')} {setup['long']} — LONG reasons:**")
                    for r in setup['long_reasons']:
                        st.markdown(f"- {r}")
                with col2:
                    st.markdown(f"**{flags.get(setup['short'],'')} {setup['short']} — SHORT reasons:**")
                    for r in setup['short_reasons']:
                        st.markdown(f"- {r}")
    else:
        st.warning("No strong confluence setups at this time. Markets may be mixed.")

    st.subheader("Currency Confluence Overview")
    conf_data = []
    for r in all_confluence:
        c = r["currency"]
        conf_data.append({
            "Currency": f"{flags.get(c,'')} {c}",
            "Direction": r["direction"],
            "Strength": r["strength"],
            "Bullish": r["bullish_count"],
            "Bearish": r["bearish_count"],
            "Reasons": " | ".join(r["reasons"])
        })
    st.dataframe(pd.DataFrame(conf_data), use_container_width=True, hide_index=True)

with tab2:
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

with tab3:
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

with tab4:
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
        st.markdown("**Seasonal Patterns — May 2026**")
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

    # Yield Curve Chart
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

with tab5:
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

st.markdown("---")
st.caption(f"AlphaFX — Institutional Grade | Macro · COT · Rates · Yield Curve · Seasonality · Confluence | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
