# src/dashboard.py
import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------------
# CONFIG
# ---------------------------
CSV_PATH = "crypto_prices.csv"
VS_CURRENCY = "usd"

st.set_page_config(
    page_title="Crypto Pro Dashboard",
    layout="wide",
    page_icon="📊"
)

st.title("📊 Crypto Professional Dashboard")
st.caption("Real-Time Market Monitoring • Trend Analysis • Portfolio • Alerts • Top Gainers/Losers")

# ---------------------------
# LOAD CSV (wide -> long)
# ---------------------------
@st.cache_data
def load_data(csv_path=CSV_PATH):
    if not os.path.exists(csv_path):
        st.error(f"CSV file not found: {csv_path}")
        return pd.DataFrame(columns=["timestamp","coin","price"])
    try:
        df_wide = pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"Cannot read CSV: {e}")
        return pd.DataFrame(columns=["timestamp","coin","price"])

    if "timestamp" not in df_wide.columns:
        st.error("CSV must have 'timestamp' column")
        return pd.DataFrame(columns=["timestamp","coin","price"])

    df_wide["timestamp"] = pd.to_datetime(df_wide["timestamp"], errors="coerce")
    coins = [c for c in df_wide.columns if c != "timestamp"]
    df_long = df_wide.melt(
        id_vars=["timestamp"],
        value_vars=coins,
        var_name="coin",
        value_name="price"
    )
    df_long["price"] = pd.to_numeric(df_long["price"], errors="coerce")
    df_long = df_long.sort_values(["coin","timestamp"]).reset_index(drop=True)
    return df_long

df = load_data()
if df.empty:
    st.stop()

coins_list = sorted(df["coin"].unique())

# ---------------------------
# SIDEBAR CONTROLS
# ---------------------------
st.sidebar.header("📌 Dashboard Controls")

selected_coin = st.sidebar.selectbox("Coin for Individual Charts", coins_list)
lookback_hours = st.sidebar.number_input("Lookback Hours", min_value=1, max_value=168, value=24)
alert_coin = st.sidebar.selectbox("Alert Coin", coins_list, index=coins_list.index(selected_coin))
alert_price = st.sidebar.number_input("Alert Price (USD)", min_value=0.0, format="%.4f")
alert_type = st.sidebar.selectbox("Alert Type", ["Goes Above", "Goes Below"])
enable_alert = st.sidebar.checkbox("Enable Alert")

# Portfolio Inputs
st.sidebar.markdown("---")
st.sidebar.header("💼 Portfolio")
portfolio = {}
for coin in coins_list:
    amt = st.sidebar.number_input(f"{coin} amount", min_value=0.0, format="%.8f", key=f"amt_{coin}")
    cost = st.sidebar.number_input(f"{coin} cost basis (USD/coin)", min_value=0.0, format="%.8f", key=f"cost_{coin}")
    if amt > 0:
        portfolio[coin] = {"amount": amt, "cost": cost}

# ---------------------------
# FILTER DATA
# ---------------------------
now = df["timestamp"].max()
start_time = now - pd.Timedelta(hours=lookback_hours)
df_filtered = df[df["timestamp"] >= start_time]
df_selected = df_filtered[df_filtered["coin"] == selected_coin]

# ---------------------------
# LIVE SNAPSHOT
# ---------------------------
st.subheader("💰 Latest Prices (All Coins)")
latest_prices = df.groupby("coin").tail(1).set_index("coin")[["price"]]
st.dataframe(latest_prices.style.format({"price":"${:,.6f}"}))

# ---------------------------
# ALERT SYSTEM
# ---------------------------
st.subheader("🔔 Single Alert")
alert_triggered = False
if enable_alert and alert_price > 0:
    latest_price_alert = float(df.loc[df["coin"]==alert_coin].sort_values("timestamp").tail(1)["price"])
    if alert_type=="Goes Above" and latest_price_alert >= alert_price:
        alert_triggered = True
        st.error(f"🔔 ALERT: {alert_coin.upper()} ≥ ${alert_price:.4f} (Current: ${latest_price_alert:.4f})")
    elif alert_type=="Goes Below" and latest_price_alert <= alert_price:
        alert_triggered = True
        st.error(f"🔔 ALERT: {alert_coin.upper()} ≤ ${alert_price:.4f} (Current: ${latest_price_alert:.4f})")
if not alert_triggered and enable_alert:
    st.success("No alerts triggered.")

# ---------------------------
# INDIVIDUAL COIN TREND
# ---------------------------
st.subheader(f"📈 {selected_coin.upper()} Trend")
if not df_selected.empty:
    fig = px.line(df_selected, x="timestamp", y="price", title=f"{selected_coin.upper()} Price Trend")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data for selected coin.")

# ---------------------------
# HISTORICAL CHART COMPARISON FOR SELECTED COIN VS OTHERS
# ---------------------------
st.subheader(f"📊 Historical Comparison: {selected_coin.upper()} vs Others")
df_compare = df_filtered.pivot(index="timestamp", columns="coin", values="price")
if selected_coin in df_compare.columns:
    df_compare_norm = df_compare / df_compare[selected_coin].iloc[0]  # Normalize to selected coin
    fig_compare = go.Figure()
    for coin in df_compare_norm.columns:
        fig_compare.add_trace(go.Scatter(x=df_compare_norm.index, y=df_compare_norm[coin], mode="lines", name=coin))
    fig_compare.update_layout(title=f"{selected_coin.upper()} vs All Coins (Normalized)", yaxis_title="Relative Price")
    st.plotly_chart(fig_compare, use_container_width=True)
else:
    st.info("Selected coin not in historical data.")

# ---------------------------
# PORTFOLIO SNAPSHOT
# ---------------------------
st.subheader("💼 Portfolio Snapshot")
if portfolio:
    rows = []
    total_value = 0.0
    total_cost = 0.0
    for coin, info in portfolio.items():
        amt = info["amount"]
        cost = info["cost"]
        live_price = latest_prices.loc[coin]["price"] if coin in latest_prices.index else np.nan
        value = live_price*amt if not np.isnan(live_price) else np.nan
        rows.append({"coin": coin, "amount": amt, "live_price": live_price, "value": value, "cost_basis": cost})
        total_value += 0 if np.isnan(value) else value
        total_cost += cost*amt
    pf_df = pd.DataFrame(rows).set_index("coin")
    st.metric("Total Portfolio Value (USD)", f"${total_value:,.2f}")
    st.metric("Total Invested (USD)", f"${total_cost:,.2f}")
    st.metric("Unrealized P/L (USD)", f"${total_value-total_cost:,.2f}")
    st.table(pf_df.style.format({
        "live_price":"${:,.6f}",
        "value":"${:,.2f}",
        "cost_basis":"${:,.6f}"
    }))
else:
    st.info("Enter holdings in the sidebar to compute portfolio value.")

# ---------------------------
# ANALYTICAL METRICS & TOP GAINERS/LOSERS
# ---------------------------
st.subheader("📊 Metrics & Top Movers")
metrics = []
for coin in coins_list:
    df_coin = df_filtered[df_filtered["coin"]==coin].sort_values("timestamp")
    if df_coin.empty:
        continue
    prices = df_coin["price"].dropna()
    if prices.empty:
        continue
    latest = prices.iloc[-1]
    earliest = prices.iloc[0]
    pct_change = (latest-earliest)/earliest*100 if earliest!=0 else 0
    volatility = prices.pct_change().std()*100
    metrics.append({"coin": coin, "latest": latest, "pct_change": pct_change, "volatility": volatility})
metrics_df = pd.DataFrame(metrics).set_index("coin")
st.dataframe(metrics_df.style.format({
    "latest":"${:,.6f}",
    "pct_change":"{:+.2f}%",
    "volatility":"{:.2f}%"
}))

# Top 5 Gainers / Losers
top_n = 5
if not metrics_df.empty:
    st.markdown("**Top 5 Gainers / Losers (Lookback Period)**")
    gainers = metrics_df.sort_values("pct_change", ascending=False).head(top_n)
    losers = metrics_df.sort_values("pct_change", ascending=True).head(top_n)
    col1, col2 = st.columns(2)
    with col1:
        st.write("Gainers")
        st.table(gainers[["latest","pct_change"]].style.format({"latest":"${:,.6f}","pct_change":"{:+.2f}%"}))
    with col2:
        st.write("Losers")
        st.table(losers[["latest","pct_change"]].style.format({"latest":"${:,.6f}","pct_change":"{:+.2f}%"}))

# ---------------------------
# MULTI-COIN NORMALIZED CHART
# ---------------------------
st.subheader("📊 Multi-Coin Comparison (Normalized Prices)")
df_norm = df_compare / df_compare.iloc[0]  # normalize to first timestamp
fig_norm = go.Figure()
for coin in df_norm.columns:
    fig_norm.add_trace(go.Scatter(x=df_norm.index, y=df_norm[coin], mode="lines", name=coin))
fig_norm.update_layout(title="Normalized Price Comparison", yaxis_title="Relative Price")
st.plotly_chart(fig_norm, use_container_width=True)

# ---------------------------
# HISTORICAL DATA TABLE
# ---------------------------
st.subheader("📄 Historical Data Table")
st.dataframe(df_filtered, use_container_width=True)

st.caption("🔄 Refresh data manually using Streamlit's top-right refresh button.")
