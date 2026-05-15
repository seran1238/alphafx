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
from political_risk import get_political_risk_score, get_political_risk_label
from economic_regime import get_regime, get_regime_display

st.set_page_config(page_title="AlphaFX", layout="wide", page_icon="📡")

FLAGS = {"USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵",
         "CHF": "🇨🇭", "AUD": "🇦🇺", "CAD": "🇨🇦", "NZD": "🇳🇿"}

col_title, col_meta = st.columns([3, 1])
with col_title:
    st.title("📡 AlphaFX — Institutional Currency Analysis")
    st.caption("Macro · COT Extremes · Rate Differentials · Yield Curve · Seasonality · Dalio Regime · Confluence")
with col_meta:
    st.markdown(f"**{datetime.now().strftime('%d.%m.%Y %H:%M')}**")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

st.info(get_regime_display())

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 Confluence",
    "🏦 COT Extremes",
    "🌍 Macro & Rates",
    "📈 Yield Curve & Seasonality",
    "📅 Event Calendar",
    "🗞️ Political Risk",
    "📊 Economic Regime",
])

with tab1:
    st.subheader("🎯 High Confluence Trade Setups")
    st.caption("Only shows setups where macro, rates, COT, yield curve AND regime all align")
    with st.spinner("Calculating confluence..."):
        setups = get_best_confluences()
        all_confluence = [get_confluence_score(c) for c in CURRENCIES]
    if setups:
        for setup in setups[:3]:
            with st.expander(f"**{setup['trade']}** — {setup['long_strength']}", expanded=True):
                col_l, col_r = st.columns(2)
                with col_l:
                    st.markdown(f"**{FLAGS.get(setup['long'], '')} {setup['long']} — LONG reasons:**")
                    for r in setup["long_reasons"]:
                        st.markdown(f"- {r}")
                with col_r:
                    st.markdown(f"**{FLAGS.get(setup['short'], '')} {setup['short']} — SHORT reasons:**")
                    for r in setup["short_reasons"]:
                        st.markdown(f"- {r}")
    else:
        st.warning("No strong confluence setups at this time. Markets may be mixed.")
    st.subheader("Currency Confluence Overview")
    conf_data = []
    for r in all_confluence:
        c = r["currency"]
        conf_data.append({
            "Currency":  f"{FLAGS.get(c, '')} {c}",
            "Direction": r["direction"],
            "Strength":  r["strength"],
            "Bullish":   r["bullish_count"],
            "Bearish":   r["bearish_count"],
            "Factors":   r["total"],
            "Reasons":   " | ".join(r["reasons"]),
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
                    "Currency":  f"{FLAGS.get(c, '')} {c}",
                    "HF Net":    f"{data['lm_net']:,.0f}",
                    "HF %ile":   f"{data['lm_percentile']:.0f}%",
                    "HF Signal": data["lm_extreme"],
                    "AM Net":    f"{data['am_net']:,.0f}",
                    "AM %ile":   f"{data['am_percentile']:.0f}%",
                    "AM Signal": data["am_extreme"],
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
                "Currency":      f"{FLAGS.get(c, '')} {c}",
                "HF Net Change": f"{data['lm_change']:+,.0f}",
                "HF Momentum":   data["lm_momentum"],
                "AM Net Change": f"{data['am_change']:+,.0f}",
                "Open Interest": f"{data['open_interest']:,.0f}",
                "OI Signal":     data["oi_signal"],
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
            x=hist["date"], y=hist["lm_net"], name="Hedge Fund Net",
            marker_color=["#2ecc71" if v > 0 else "#e74c3c" for v in hist["lm_net"]],
        ))
        fig.add_trace(go.Scatter(
            x=hist["date"], y=hist["lm_change"].cumsum(),
            name="Cumulative Change",
            line=dict(color="#f39c12", width=2),
            yaxis="y2",
        ))
        fig.update_layout(
            title=f"{selected} — Hedge Fund Net Positioning (1 Year)",
            plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e", font_color="white",
            height=400, yaxis2=dict(overlaying="y", side="right", showgrid=False),
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
        bias_emoji  = "🟢" if r["bias"] == "Hawkish" else "🔴" if r["bias"] == "Dovish" else "🟡"
        trend_emoji = "📈" if r["trend"] == "Hiking" else "📉" if r["trend"] == "Cutting" else "➡️"
        cb_data.append({
            "Currency":    f"{FLAGS.get(c, '')} {c}",
            "Rate":        f"{r['rate']}%",
            "Bias":        f"{bias_emoji} {r['bias']}",
            "Trend":       f"{trend_emoji} {r['trend']}",
            "Last Change": r["last_change"],
        })
    st.dataframe(pd.DataFrame(cb_data), use_container_width=True, hide_index=True)
    st.markdown("**Top Rate Differentials (Carry Trade)**")
    diff_df = pd.DataFrame(differentials[:10])
    diff_df["Favor"] = diff_df["Favor"].apply(lambda x: f"{FLAGS.get(x, '')} {x}")
    st.dataframe(
        diff_df[["Pair", "Rate 1", "Rate 2", "Differential", "Favor", "Attractiveness"]],
        use_container_width=True, hide_index=True,
    )
    fig2 = go.Figure()
    for r in ranking:
        c = r["currency"]
        color = "#2ecc71" if r["bias"] == "Hawkish" else "#e74c3c" if r["bias"] == "Dovish" else "#e67e22"
        fig2.add_trace(go.Bar(
            x=[f"{FLAGS.get(c, '')} {c}"], y=[r["score"]], marker_color=color, name=c,
        ))
    fig2.update_layout(
        title="Central Bank Hawkish/Dovish Score", showlegend=False,
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e", font_color="white", height=300,
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab4:
    st.subheader("📈 Yield Curve & Seasonality")
    col_yc, col_seas = st.columns(2)
    with col_yc:
        st.markdown("**Yield Curve Analysis**")
        with st.spinner("Loading yield curves..."):
            yc_data = get_all_yield_curves()
        yc_display = []
        for r in yc_data:
            c = r["currency"]
            yc_display.append({
                "Currency":    f"{FLAGS.get(c, '')} {c}",
                "Yield Curve": r["yield_curve"],
                "Trend":       r["trend"],
                "Score":       r["score"],
            })
        st.dataframe(
            pd.DataFrame(yc_display).sort_values("Score", ascending=False),
            use_container_width=True, hide_index=True,
        )
    with col_seas:
        st.markdown(f"**Seasonal Patterns — {datetime.now().strftime('%B %Y')}**")
        seasonal = get_all_seasonality()
        seas_display = []
        for r in seasonal:
            c = r["currency"]
            seas_display.append({
                "Currency":   f"{FLAGS.get(c, '')} {c}",
                "Signal":     r["signal"],
                "This Month": r["current_month"],
                "Next Month": r["next_month"],
                "Score":      r["score"],
            })
        st.dataframe(pd.DataFrame(seas_display), use_container_width=True, hide_index=True)
    st.subheader("Seasonal Heatmap")
    import calendar as cal
    months = [cal.month_abbr[i] for i in range(1, 13)]
    from seasonality import SEASONAL_PATTERNS
    fig3 = go.Figure(data=go.Heatmap(
        z=[[SEASONAL_PATTERNS.get(c, {}).get(m, 0) for m in range(1, 13)] for c in CURRENCIES],
        x=months,
        y=[f"{FLAGS.get(c, '')} {c}" for c in CURRENCIES],
        colorscale="RdYlGn", zmid=0,
    ))
    fig3.update_layout(
        title="Currency Seasonal Patterns (Monthly Avg)",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e", font_color="white", height=350,
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
                e["currency"] = f"{FLAGS.get(c, '')} {c}"
                all_events.append(e)
    if all_events:
        events_df = pd.DataFrame(all_events).sort_values("date")
        st.dataframe(
            events_df[["date", "currency", "event", "impact", "previous", "estimate"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No upcoming high impact events found or API limit reached.")

with tab6:
    st.subheader("🗞️ Political Risk — GDELT Media Tone")
    st.caption("Source: GDELT Global Knowledge Graph · 7-day rolling media sentiment")
    with st.spinner("Fetching GDELT data..."):
        pol_rows = []
        pol_headlines_map = {}
        for c in CURRENCIES:
            score, headlines = get_political_risk_score(c)
            label = get_political_risk_label(score)
            pol_rows.append({
                "Currency": f"{FLAGS.get(c, '')} {c}",
                "Score":    score,
                "Risk":     label,
            })
            pol_headlines_map[c] = headlines
    pol_df = pd.DataFrame(pol_rows).sort_values("Score", ascending=False)
    st.dataframe(pol_df, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.markdown("**Recent Headlines by Currency**")
    for row in pol_rows:
        c_raw = row["Currency"].split()[-1]
        headlines = pol_headlines_map.get(c_raw, [])
        if headlines:
            with st.expander(f"{row['Currency']}  ·  {row['Risk']}"):
                for h in headlines:
                    st.markdown(f"- {h}")
    fig_pol = go.Figure()
    fig_pol.add_trace(go.Bar(
        x=pol_df["Currency"],
        y=pol_df["Score"],
        marker_color=["#2ecc71" if s >= 0 else "#e74c3c" for s in pol_df["Score"]],
    ))
    fig_pol.update_layout(
        title="Political Risk Score (GDELT Tone · 7d)",
        yaxis_title="Score (positive = calm, negative = risk)",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=320, showlegend=False,
    )
    st.plotly_chart(fig_pol, use_container_width=True)

with tab7:
    st.subheader("📊 Dalio Economic Regime")
    st.caption("Based on Ray Dalio's Economic Machine — Growth × Inflation momentum (FRED data)")
    regime = get_regime()
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Regime", f"{regime['emoji']} {regime['regime']}")
    with col_b:
        g = f"{regime['growth_mom']:+.2f}%" if regime["growth_mom"] is not None else "N/A"
        st.metric("Growth Momentum (3m IP)", g)
    with col_c:
        i = f"{regime['inflation_mom']:+.2f}%" if regime["inflation_mom"] is not None else "N/A"
        st.metric("Inflation Momentum (3m CPI)", i)
    st.info(regime["description"])
    quad_colors = {
        "Goldilocks": "#2ecc71",
        "Reflation":  "#f39c12",
        "Stagflation": "#e74c3c",
        "Deflation":  "#3498db",
    }
    current = regime["regime"]
    fig_quad = go.Figure()
    annotations = [
        ("🌤️ Goldilocks",   1,  1, "Growth↑ Inflation↓"),
        ("🔥 Reflation",    1, -1, "Growth↑ Inflation↑"),
        ("⚠️ Stagflation", -1, -1, "Growth↓ Inflation↑"),
        ("❄️ Deflation",   -1,  1, "Growth↓ Inflation↓"),
    ]
    for label, x, y, sub in annotations:
        name = label.split()[-1]
        fig_quad.add_shape(
            type="rect",
            x0=x * 0.05, x1=x, y0=y * 0.05, y1=y,
            fillcolor=quad_colors.get(name, "#555"),
            opacity=0.9 if name == current else 0.25,
            line_width=3 if name == current else 0,
            line_color="white",
        )
        fig_quad.add_annotation(
            x=x * 0.55, y=y * 0.6,
            text=f"<b>{label}</b><br><span style='font-size:10px'>{sub}</span>",
            showarrow=False, font=dict(color="white", size=13),
        )
    gm_n = max(-1, min(1, (regime["growth_mom"] or 0) / 3))
    im_n = max(-1, min(1, (regime["inflation_mom"] or 0) / 3))
    fig_quad.add_annotation(
        x=gm_n, y=im_n, ax=0, ay=0,
        xref="x", yref="y", axref="x", ayref="y",
        text="📍 Current", showarrow=True, arrowhead=3, arrowsize=2,
        arrowcolor="white", font=dict(color="white", size=12),
    )
    fig_quad.update_layout(
        xaxis=dict(range=[-1.15, 1.15], zeroline=True, zerolinecolor="white",
                   zerolinewidth=2, showticklabels=False, title="Growth →"),
        yaxis=dict(range=[-1.15, 1.15], zeroline=True, zerolinecolor="white",
                   zerolinewidth=2, showticklabels=False, title="Inflation →"),
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=420, margin=dict(l=60, r=40, t=40, b=60),
        title="Current Macro Regime",
    )
    st.plotly_chart(fig_quad, use_container_width=True)
    st.markdown("**Currency Bias in Current Regime**")
    bias_rows = []
    for c, score in regime["currency_bias"].items():
        arrow = "🟢 Tailwind" if score >= 15 else "🟡 Mild +" if score >= 5 \
            else "🔴 Headwind" if score <= -15 else "🟠 Mild −" if score <= -5 else "⚪ Neutral"
        bias_rows.append({
            "Currency":          f"{FLAGS.get(c, '')} {c}",
            "Regime Bias Score": score,
            "Signal":            arrow,
        })
    bias_df = pd.DataFrame(bias_rows).sort_values("Regime Bias Score", ascending=False)
    st.dataframe(bias_df, use_container_width=True, hide_index=True)
    fig_bias = go.Figure(go.Bar(
        x=bias_df["Currency"],
        y=bias_df["Regime Bias Score"],
        marker_color=["#2ecc71" if s > 0 else "#e74c3c" for s in bias_df["Regime Bias Score"]],
    ))
    fig_bias.update_layout(
        title=f"Regime Bias — {regime['emoji']} {regime['regime']}",
        yaxis_title="Bias Score",
        plot_bgcolor="#1e1e2e", paper_bgcolor="#1e1e2e",
        font_color="white", height=300, showlegend=False,
    )
    st.plotly_chart(fig_bias, use_container_width=True)

st.markdown("---")
st.caption(
    f"AlphaFX — Institutional Grade  |  "
    f"Macro · COT · Rates · Yield Curve · Seasonality · GDELT Political Risk · Dalio Regime · Confluence  |  "
    f"{datetime.now().strftime('%d.%m.%Y %H:%M')}"
)
