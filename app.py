"""Nassau Candy - Product Line Profitability Dashboard.   Run:  streamlit run app.py"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import add_flags, clean_data, division_metrics, pareto, product_metrics, quadrant

st.set_page_config(page_title="Nassau Candy | Profit Lab", page_icon="🍬", layout="wide")

PALETTE = ["#D81B60", "#8E24AA", "#00897B", "#F9A825", "#1E88E5", "#6D4C41", "#546E7A"]
FLAG_COLORS = {"Healthy": "#00897B", "Low volume - monitor": "#F9A825",
               "Reprice / renegotiate cost": "#EF6C00", "Discontinuation review": "#C62828"}
px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = PALETTE

st.markdown("""
<style>
.hero {background: linear-gradient(120deg,#D81B60 0%,#8E24AA 60%,#5E35B1 100%); padding: 26px 32px;
       border-radius: 16px; color: white; margin-bottom: 18px;}
.hero h1 {color: white; margin: 0; font-size: 2rem;}
.hero p {margin: 6px 0 0 0; opacity: .92;}
.kpi {background: white; border-radius: 14px; padding: 14px 18px; border-left: 6px solid #D81B60;
      box-shadow: 0 2px 8px rgba(0,0,0,.08);}
.kpi-l {font-size: .78rem; color: #777; text-transform: uppercase; letter-spacing: .06em;}
.kpi-v {font-size: 1.7rem; font-weight: 700; color: #2D2A32;}
.kpi-s {font-size: .78rem; color: #999;}
.stTabs [data-baseweb="tab"] {font-weight: 600;}
</style>
""", unsafe_allow_html=True)


def kpi(col, label, value, sub=""):
    col.markdown(f'<div class="kpi"><div class="kpi-l">{label}</div><div class="kpi-v">{value}</div>'
                 f'<div class="kpi-s">{sub}</div></div>', unsafe_allow_html=True)


@st.cache_data
def load():
    df, _ = clean_data()
    return df


df = load()

# ---------------- sidebar filters ----------------
st.sidebar.title("🍬 Filters")
dmin, dmax = df["Order Date"].min().date(), df["Order Date"].max().date()
dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
start, end = (dr[0], dr[1]) if isinstance(dr, (tuple, list)) and len(dr) == 2 else (dmin, dmax)
all_divs = sorted(df["Division"].unique())
divs = st.sidebar.multiselect("Division", all_divs, default=all_divs)
thr = st.sidebar.slider("Margin threshold (%)", 0, 100, 50)
search = st.sidebar.text_input("Search product")
st.sidebar.caption("Every chart and table on every tab follows these filters.")

f = df[(df["Order Date"].dt.date >= start) & (df["Order Date"].dt.date <= end) & (df["Division"].isin(divs))]
if search:
    f = f[f["Product Name"].str.contains(search, case=False, na=False)]

st.markdown(f"""<div class="hero"><h1>Nassau Candy Profit Lab</h1>
<p>Which products really make money? Product line profitability and margin performance,
{start:%d %b %Y} to {end:%d %b %Y}</p></div>""", unsafe_allow_html=True)

if f.empty:
    st.warning("No data for the selected filters. Change the filters in the sidebar.")
    st.stop()

pm = quadrant(add_flags(product_metrics(f), margin_threshold=thr))
dm = division_metrics(f)
tot_s, tot_p = f["Sales"].sum(), f["Gross Profit"].sum()

k = st.columns(5)
kpi(k[0], "Total sales", f"{tot_s:,.0f}", f"{len(f):,} order lines")
kpi(k[1], "Gross profit", f"{tot_p:,.0f}")
kpi(k[2], "Gross margin", f"{tot_p / tot_s * 100:.1f}%", f"threshold set at {thr}%")
kpi(k[3], "Units sold", f"{f['Units'].sum():,}", f"profit/unit {tot_p / f['Units'].sum():.2f}")
kpi(k[4], "Products flagged", f"{(pm['Risk Flag'] != 'Healthy').sum()} / {len(pm)}", "see Cost vs Margin tab")
st.write("")

tabs = st.tabs(["Product Profitability", "Division Performance", "Cost vs Margin", "Profit Concentration",
                "Trends & Volatility", "Factory & Geography", "Insights & Actions"])

# ---------------- TAB 1: product profitability ----------------
with tabs[0]:
    st.subheader("Product margin leaderboard")
    lb = pm.sort_values("Margin %", ascending=False)
    st.dataframe(lb[["Product Name", "Division", "Sales", "Profit", "Margin %", "Profit per Unit",
                     "Revenue Contribution %", "Profit Contribution %", "Margin Volatility (std pts)",
                     "Quadrant"]].round(2), hide_index=True)
    st.download_button("Download product metrics (CSV)", pm.to_csv(index=False).encode(),
                       "product_metrics.csv", "text/csv")
    c1, c2 = st.columns(2)
    s = pm.sort_values("Margin %")
    fig = px.bar(s, x="Margin %", y="Product Name", orientation="h", title="Gross margin by product",
                 color=s["Margin %"] < thr, color_discrete_map={True: "#C62828", False: "#8E24AA"},
                 labels={"color": f"Below {thr}%"})
    c1.plotly_chart(fig)
    s = pm.sort_values("Profit")
    c2.plotly_chart(px.bar(s, x="Profit", y="Product Name", orientation="h", title="Profit contribution by product",
                           color_discrete_sequence=["#D81B60"]))
    qcolors = {"Star (high sales, high margin)": "#2E7D32", "Volume trap (high sales, low margin)": "#F9A825",
               "Niche / growth (low sales, high margin)": "#1E88E5", "Weak (low sales, low margin)": "#E53935"}
    fig = px.scatter(pm, x="Sales", y="Margin %", color="Quadrant", color_discrete_map=qcolors,
                     hover_name="Product Name", log_x=True, title="Sales vs margin quadrant (split at medians)")
    fig.update_traces(marker=dict(size=16, line=dict(width=1, color="white")))
    fig.update_xaxes(dtick=1)
    st.plotly_chart(fig)
    st.caption("Hover over a dot to see the product name. Quadrants are relative (median of the products shown).")

# ---------------- TAB 2: division ----------------
with tabs[1]:
    st.subheader("Division performance")
    c1, c2 = st.columns(2)
    long = dm.melt(id_vars="Division", value_vars=["Sales", "Profit"], var_name="Metric", value_name="Value")
    c1.plotly_chart(px.bar(long, x="Division", y="Value", color="Metric", barmode="group",
                           title="Revenue vs profit by division"))
    c2.plotly_chart(px.box(f, x="Division", y="Margin %", color="Division",
                           title="Order-line margin distribution by division"))
    st.dataframe(dm.round(2), hide_index=True)
    st.caption("Share Gap = profit share minus revenue share. Negative = the division earns less profit than "
               "its revenue share (structural margin issue).")
    sh = dm.melt(id_vars="Division", value_vars=["Revenue Share %", "Profit Share %"], var_name="Share", value_name="%")
    st.plotly_chart(px.bar(sh, x="Division", y="%", color="Share", barmode="group", title="Revenue share vs profit share"))

# ---------------- TAB 3: cost vs margin ----------------
with tabs[2]:
    st.subheader("Cost vs sales")
    samp = f.sample(min(5000, len(f)), random_state=1)
    fig = px.scatter(samp, x="Sales", y="Cost", color="Division", hover_data=["Product Name"], opacity=0.5,
                     title="Cost vs sales per order line (dashed = break-even)")
    mx = float(samp["Sales"].max())
    fig.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode="lines", line=dict(dash="dash", color="red"), name="Break-even"))
    st.plotly_chart(fig)

    st.subheader("Margin risk flags")
    st.caption(f"Rules: margin < {thr}% and revenue share < 1% -> Discontinuation review; "
               f"margin < {thr}% otherwise -> Reprice / renegotiate cost; revenue share < 1% -> Low volume - monitor.")
    st.plotly_chart(px.scatter(pm, x="Cost Ratio %", y="Profit per Unit", color="Risk Flag",
                               color_discrete_map=FLAG_COLORS, hover_name="Product Name",
                               title="Cost ratio vs profit per unit (hover for product)").update_traces(
        marker=dict(size=15, line=dict(width=1, color="white"))))
    st.dataframe(pm[["Product Name", "Sales", "Margin %", "Cost Ratio %", "Profit per Unit", "Risk Flag"]].round(2),
                 hide_index=True)

    st.subheader("Repricing opportunity")
    t = min(thr, 95) / 100
    rp = pm[pm["Margin %"] < thr].copy()
    if rp.empty:
        st.success("No product is below the margin threshold.")
    else:
        rp["Price rise needed (%)"] = (rp["Cost"] / (1 - t) / rp["Sales"] - 1) * 100
        rp["Extra profit if repriced"] = rp["Cost"] / (1 - t) - rp["Sales"]
        st.dataframe(rp[["Product Name", "Sales", "Margin %", "Price rise needed (%)",
                         "Extra profit if repriced", "Risk Flag"]].round(2), hide_index=True)
        st.caption("Price rise needed to reach the threshold margin, with unit volume unchanged "
                   "(no demand reaction assumed).")

    st.subheader("What-if: price change")
    prod = st.selectbox("Product", pm["Product Name"].tolist())
    pct = st.slider("Price change (%)", -20, 30, 5)
    r = pm[pm["Product Name"] == prod].iloc[0]
    new_profit = r["Profit"] + r["Sales"] * pct / 100
    new_margin = new_profit / (r["Sales"] * (1 + pct / 100)) * 100
    w = st.columns(3)
    w[0].metric("Current profit", f"{r['Profit']:,.0f}")
    w[1].metric("Projected profit", f"{new_profit:,.0f}", f"{new_profit - r['Profit']:,.0f}")
    w[2].metric("Projected margin", f"{new_margin:.1f}%", f"{new_margin - r['Margin %']:.1f} pts")
    st.caption("Assumes unit volume stays the same (no demand reaction).")

# ---------------- TAB 4: pareto ----------------
with tabs[3]:
    st.subheader("Pareto analysis")
    metric = st.radio("Metric", ["Profit", "Sales"], horizontal=True)
    p, n80 = pareto(pm, metric)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=p["Product Name"], y=p[metric], name=metric, marker_color="#8E24AA"))
    fig.add_trace(go.Scatter(x=p["Product Name"], y=p["Cumulative %"], name="Cumulative %", yaxis="y2",
                             mode="lines+markers", line=dict(color="#D81B60")))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Cumulative %"),
                      title=f"Pareto chart - {metric}")
    fig.add_hline(y=80, line_dash="dash", line_color="gray", yref="y2")
    st.plotly_chart(fig)
    share_col = "Profit Contribution %" if metric == "Profit" else "Revenue Contribution %"
    top1 = p.iloc[0][share_col]
    top3 = p.head(3)[share_col].sum()
    d = st.columns(4)
    kpi(d[0], f"Products for 80% of {metric.lower()}", f"{n80} of {len(p)}")
    kpi(d[1], "Share of product range", f"{n80 / len(p) * 100:.0f}%")
    kpi(d[2], "Top product share", f"{top1:.1f}%")
    kpi(d[3], "Top 3 share", f"{top3:.1f}%")
    st.write("")
    if top1 > 25 or top3 > 60:
        st.error("Dependency risk: a small number of products drive most of the business.")
    else:
        st.success("Concentration looks moderate.")
    st.dataframe(dm[["Division", "Revenue Share %", "Profit Share %"]].round(2), hide_index=True)

# ---------------- TAB 5: trends & volatility ----------------
with tabs[4]:
    st.subheader("Monthly sales, profit and margin")
    mm = f.groupby("Month").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum")).reset_index()
    mm["Margin %"] = mm["Profit"] / mm["Sales"] * 100
    fig = go.Figure()
    fig.add_trace(go.Bar(x=mm["Month"], y=mm["Sales"], name="Sales", marker_color="#E1BEE7"))
    fig.add_trace(go.Bar(x=mm["Month"], y=mm["Profit"], name="Profit", marker_color="#8E24AA"))
    fig.add_trace(go.Scatter(x=mm["Month"], y=mm["Margin %"], name="Margin %", yaxis="y2",
                             mode="lines+markers", line=dict(color="#D81B60")))
    fig.update_layout(barmode="group", yaxis2=dict(overlaying="y", side="right", title="Margin %"),
                      title="Monthly performance")
    st.plotly_chart(fig)

    st.subheader("Margin volatility")
    vol = pm.dropna(subset=["Margin Volatility (std pts)"]).sort_values("Margin Volatility (std pts)")
    if vol.empty:
        st.info("Not enough months of data for volatility with the current filters.")
    else:
        st.plotly_chart(px.bar(vol, x="Margin Volatility (std pts)", y="Product Name", orientation="h",
                               title="Std deviation of monthly margin (percentage points)",
                               color_discrete_sequence=["#00897B"]))
        st.caption("Higher = margin swings more from month to month. Needs at least 3 active months per product.")
    pick = st.multiselect("Compare monthly margin of products", pm["Product Name"].tolist(),
                          default=pm["Product Name"].head(3).tolist())
    if pick:
        pmn = f[f["Product Name"].isin(pick)].groupby(["Product Name", "Month"]).agg(
            S=("Sales", "sum"), P=("Gross Profit", "sum")).reset_index()
        pmn["Margin %"] = pmn["P"] / pmn["S"] * 100
        st.plotly_chart(px.line(pmn, x="Month", y="Margin %", color="Product Name", markers=True,
                                title="Monthly margin by product"))

# ---------------- TAB 6: factory & geography ----------------
with tabs[5]:
    st.subheader("Factory profitability")
    fa = f.groupby("Factory").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum"),
                                  Products=("Product Name", "nunique")).reset_index()
    fa["Margin %"] = fa["Profit"] / fa["Sales"] * 100
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(fa.sort_values("Margin %"), x="Margin %", y="Factory", orientation="h",
                           title="Margin by factory", color_discrete_sequence=["#D81B60"]))
    long = fa.melt(id_vars="Factory", value_vars=["Sales", "Profit"], var_name="Metric", value_name="Value")
    c2.plotly_chart(px.bar(long, x="Factory", y="Value", color="Metric", barmode="group",
                           title="Sales vs profit by factory"))
    st.dataframe(fa.round(2), hide_index=True)

    st.subheader("Geography")
    reg = f.groupby(["Region", "Division"]).agg(S=("Sales", "sum"), P=("Gross Profit", "sum")).reset_index()
    reg["Margin %"] = reg["P"] / reg["S"] * 100
    st.plotly_chart(px.density_heatmap(reg, x="Division", y="Region", z="Margin %", histfunc="avg",
                                       text_auto=".1f", color_continuous_scale="Purples",
                                       title="Margin % by region and division"))
    stt = f.groupby("State/Province").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum")).reset_index()
    stt["Margin %"] = stt["Profit"] / stt["Sales"] * 100
    top = stt.sort_values("Profit", ascending=False).head(10).sort_values("Profit")
    st.plotly_chart(px.bar(top, x="Profit", y="State/Province", orientation="h", title="Top 10 states by profit",
                           color_discrete_sequence=["#8E24AA"]))
    sm = f.groupby("Ship Mode").agg(Sales=("Sales", "sum"), Profit=("Gross Profit", "sum")).reset_index()
    sm["Margin %"] = sm["Profit"] / sm["Sales"] * 100
    st.plotly_chart(px.bar(sm, x="Ship Mode", y="Margin %", title="Margin by ship mode",
                           color_discrete_sequence=["#00897B"]))

# ---------------- TAB 7: insights ----------------
with tabs[6]:
    st.subheader("Insights & recommended actions")
    st.caption("Generated live from the current filters, so the text changes when you change the sidebar.")
    top_p = pm.iloc[0]
    low_p = pm.sort_values("Margin %").iloc[0]
    _, n80p = pareto(pm, "Profit")
    st.success(f"**Profit driver:** {top_p['Product Name']} earns {top_p['Profit']:,.0f} "
               f"({top_p['Profit Contribution %']:.1f}% of profit) at a {top_p['Margin %']:.1f}% margin.")
    st.info(f"**Concentration:** {n80p} of {len(pm)} products generate 80% of profit.")
    if low_p["Margin %"] < thr:
        st.error(f"**Margin risk:** {low_p['Product Name']} has only a {low_p['Margin %']:.1f}% margin "
                 f"({low_p['Profit per Unit']:.2f} profit per unit on {low_p['Units']:,} units).")
    gap = dm.sort_values("Share Gap (pts)").iloc[0]
    if gap["Share Gap (pts)"] < -0.5:
        st.warning(f"**Division imbalance:** {gap['Division']} has {gap['Revenue Share %']:.1f}% of revenue "
                   f"but {gap['Profit Share %']:.1f}% of profit.")
    fa2 = f.groupby("Factory").agg(S=("Sales", "sum"), P=("Gross Profit", "sum"))
    fa2["m"] = fa2["P"] / fa2["S"] * 100
    st.warning(f"**Weakest factory:** {fa2['m'].idxmin()} runs at a {fa2['m'].min():.1f}% margin "
               f"(best: {fa2['m'].idxmax()} at {fa2['m'].max():.1f}%).")
    st.subheader("Action list")
    act = pm[pm["Risk Flag"] != "Healthy"][["Product Name", "Risk Flag", "Margin %", "Sales"]].round(2)
    if act.empty:
        st.success("No actions needed at this threshold.")
    else:
        st.dataframe(act, hide_index=True)
        st.download_button("Download action list (CSV)", act.to_csv(index=False).encode(),
                           "action_list.csv", "text/csv")
