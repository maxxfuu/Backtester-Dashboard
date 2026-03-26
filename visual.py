import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import json
import re
import io
import numpy as np

st.set_page_config(
    page_title="Backtester Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_BG = "#0a0e17"
PANEL_BG = "#0f1520"
GRID_COLOR = "#1a2235"
MID_COLOR = "#e8c547"
BID_COLOR = "#00e5a0"
ASK_COLOR = "#ff4d6a"
BUY_COLOR = "#00ff88"
SELL_COLOR = "#ff3355"
PNL_COLOR = "#00bfff"
DRAWDOWN_COLOR = "rgba(255,65,100,0.25)"
RIBBON_BID = "rgba(0,229,160,0.12)"
RIBBON_ASK = "rgba(255,77,106,0.12)"
INVENTORY_COLOR = "#7c5cfc"
ZERO_LINE = "rgba(255,255,255,0.15)"
TEXT_COLOR = "#c0ccd8"
FONT = "JetBrains Mono, Fira Code, monospace"

PLOTLY_LAYOUT = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=PANEL_BG,
    font=dict(family=FONT, color=TEXT_COLOR, size=11),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    margin=dict(l=60, r=30, t=40, b=30),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
    hovermode="x unified",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&display=swap');
    .stApp { background-color: #0a0e17; }
    [data-testid="stSidebar"] { background-color: #0f1520; border-right: 1px solid #1a2235; }
    [data-testid="stSidebar"] * { color: #c0ccd8 !important; }
    h1, h2, h3 { font-family: 'JetBrains Mono', monospace !important; }
    .header-glow { text-align: center; font-family: 'JetBrains Mono', monospace;
        font-size: 2rem; font-weight: 700; letter-spacing: 0.12em;
        background: linear-gradient(90deg, #00e5a0, #e8c547, #ff4d6a);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-shadow: 0 0 40px rgba(232,197,71,0.3); margin-bottom: 0; }
    .sub-glow { text-align: center; font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem; color: #556677; letter-spacing: 0.25em;
        margin-top: -4px; margin-bottom: 24px; }
    .metric-card { background: #0f1520; border: 1px solid #1a2235; border-radius: 8px;
        padding: 14px 18px; text-align: center; position: relative; cursor: default; }
    .metric-card .label { font-size: 0.7rem; color: #556677; letter-spacing: 0.15em;
        text-transform: uppercase; font-family: 'JetBrains Mono', monospace; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; color: #e8c547; margin-top: 4px; }
    .metric-card .value.green { color: #00e5a0; }
    .metric-card .value.red { color: #ff4d6a; }
    .metric-card .tooltip-text { visibility: hidden; opacity: 0; position: absolute;
        bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%);
        background: #1a2235; color: #c0ccd8; font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem; letter-spacing: 0.03em; line-height: 1.5;
        padding: 10px 14px; border-radius: 6px; border: 1px solid #2a3a55;
        white-space: normal; width: 220px; z-index: 1000;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        transition: opacity 0.2s ease, visibility 0.2s ease; text-align: left; }
    .metric-card .tooltip-text::after { content: ''; position: absolute;
        top: 100%; left: 50%; transform: translateX(-50%);
        border: 6px solid transparent; border-top-color: #1a2235; }
    .metric-card:hover .tooltip-text { visibility: visible; opacity: 1; }
    .metric-card.dd-clickable { cursor: pointer; transition: border-color 0.2s ease; }
    .metric-card.dd-clickable:hover { border-color: #ff4d6a; }
    div[data-testid="stFileUploader"] label { color: #c0ccd8 !important;
        font-family: 'JetBrains Mono', monospace !important; }
    .stSelectbox label, .stMultiSelect label { color: #c0ccd8 !important;
        font-family: 'JetBrains Mono', monospace !important; }

    /* ── Sidebar widget overrides ── */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: #1a2235 !important; border: 1px solid #2a3a55 !important;
        color: #c0ccd8 !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] span { color: #c0ccd8 !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] svg { fill: #556677 !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"]:hover svg { fill: #ff4d6a !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #0f1520 !important; border-color: #1a2235 !important; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
        border-color: #2a3a55 !important; box-shadow: 0 0 0 1px #2a3a55 !important; }
    [data-testid="stSidebar"] [data-baseweb="popover"] > div { background-color: #0f1520 !important; }
    [data-testid="stSidebar"] [role="listbox"] { background-color: #0f1520 !important; }
    [data-testid="stSidebar"] [role="option"] { background-color: #0f1520 !important; color: #c0ccd8 !important; }
    [data-testid="stSidebar"] [role="option"]:hover { background-color: #1a2235 !important; }
    [data-testid="stSidebar"] [data-baseweb="icon"] svg { fill: #556677 !important; }

    /* ── Slider ── */
    [data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {
        background-color: #1a2235 !important; border-color: #2a3a55 !important;
        box-shadow: none !important; width: 12px !important; height: 12px !important; }
    [data-testid="stSidebar"] [data-baseweb="slider"] div[data-testid="stThumbValue"] {
        color: #556677 !important; }
    [data-testid="stSidebar"] [data-baseweb="slider"] div > div > div {
        background: #1a2235 !important; }
    [data-testid="stSidebar"] [data-baseweb="slider"] div > div > div > div {
        background: #2a3a55 !important; }

    /* ── File uploader ── */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background-color: #0f1520 !important; border-color: #1a2235 !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background-color: #1a2235 !important; color: #c0ccd8 !important;
        border-color: #2a3a55 !important; }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button:hover {
        background-color: #2a3a55 !important; border-color: #3a4a65 !important; }
    [data-testid="stSidebar"] small { color: #556677 !important; }
</style>
""", unsafe_allow_html=True)


# ─── Parsers ───────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def parse_prices_csv(file_bytes: bytes) -> pd.DataFrame:
    text = file_bytes.decode("utf-8")
    df = pd.read_csv(io.StringIO(text), sep=";")
    return _coerce_numeric_columns(df)


def _coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if "price" in col or "volume" in col or col in ("mid_price", "profit_and_loss"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def parse_log_file(file_bytes: bytes):
    text = file_bytes.decode("utf-8")

    activities_df = None
    trades_list = []
    sandbox_entries = []

    # ── Try JSON envelope format (performance tester / submission result) ──
    json_parsed = False
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            envelope = json.loads(stripped)
            if "activitiesLog" in envelope or "tradeHistory" in envelope:
                json_parsed = True
                act_csv = envelope.get("activitiesLog", "")
                if act_csv:
                    activities_df = _coerce_numeric_columns(
                        pd.read_csv(io.StringIO(act_csv), sep=";")
                    )
                trades_list = envelope.get("tradeHistory", [])
                sandbox_entries = envelope.get("logs", [])
        except (json.JSONDecodeError, ValueError):
            pass

    # ── Fallback: plain-text backtester log format ──
    if not json_parsed:
        act_match = text.find("Activities log:\n")
        trade_match = text.find("Trade History:\n")

        if act_match != -1:
            act_start = act_match + len("Activities log:\n")
            act_end = trade_match if trade_match != -1 else len(text)
            act_text = text[act_start:act_end].strip()
            if act_text:
                activities_df = _coerce_numeric_columns(
                    pd.read_csv(io.StringIO(act_text), sep=";")
                )

        if trade_match != -1:
            trade_start = trade_match + len("Trade History:\n")
            trade_text = text[trade_start:].strip()
            trade_text = re.sub(r",(\s*[}\]])", r"\1", trade_text)
            try:
                trades_list = json.loads(trade_text)
            except json.JSONDecodeError:
                trades_list = []

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("{") and '"lambdaLog"' in line:
                try:
                    entry = json.loads(line)
                    sandbox_entries.append(entry)
                except json.JSONDecodeError:
                    pass

        if not sandbox_entries:
            block = ""
            in_block = False
            for line in text.split("\n"):
                s = line.strip()
                if s == "{" or (s.startswith("{") and '"sandboxLog"' in s):
                    in_block = True
                    block = s
                elif in_block:
                    block += s
                    if s == "}":
                        in_block = False
                        try:
                            entry = json.loads(block)
                            if "lambdaLog" in entry:
                                sandbox_entries.append(entry)
                        except json.JSONDecodeError:
                            pass
                        block = ""

    orders_by_ts = {}
    positions_by_ts = {}
    for entry in sandbox_entries:
        ts = entry.get("timestamp", 0)
        lambda_log = entry.get("lambdaLog", "")
        if not lambda_log:
            continue
        try:
            parsed = json.loads(lambda_log)
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(parsed, list):
            continue

        state_arr = parsed[0] if len(parsed) > 0 else []
        orders_arr = parsed[1] if len(parsed) > 1 else []

        if orders_arr:
            for o in orders_arr:
                if len(o) >= 3:
                    product, price, qty = o[0], o[1], o[2]
                    orders_by_ts.setdefault(ts, []).append(
                        {"product": product, "price": price, "quantity": qty}
                    )

        if isinstance(state_arr, list) and len(state_arr) > 6:
            pos_dict = state_arr[6]
            if isinstance(pos_dict, dict):
                for prod, pos in pos_dict.items():
                    positions_by_ts.setdefault(ts, {})[prod] = pos

    return activities_df, trades_list, orders_by_ts, positions_by_ts


# ─── Chart builders ────────────────────────────────────────────────────────────

def build_charts(prices_df, trades_df, product, orders_by_ts, positions_by_ts, dd_highlight=None):
    pdf = prices_df[prices_df["product"] == product].copy().sort_values("timestamp")
    pdf = pdf.reset_index(drop=True)

    if pdf.empty:
        st.warning(f"No price data for **{product}**.")
        return

    ts = pdf["timestamp"]
    mid = pdf["mid_price"]
    best_bid = pdf["bid_price_1"]
    best_ask = pdf["ask_price_1"]
    pnl = pdf["profit_and_loss"]

    # ── Trades ──
    buy_ts, buy_px, sell_ts, sell_px = [], [], [], []
    if trades_df is not None and not trades_df.empty:
        ptrades = trades_df[trades_df["symbol"] == product]
        for _, row in ptrades.iterrows():
            if row.get("buyer") == "SUBMISSION":
                buy_ts.append(row["timestamp"])
                buy_px.append(row["price"])
            elif row.get("seller") == "SUBMISSION":
                sell_ts.append(row["timestamp"])
                sell_px.append(row["price"])

    # ── Inventory ──
    inv_ts, inv_vals = [], []
    for t in sorted(positions_by_ts.keys()):
        pos = positions_by_ts[t]
        if product in pos:
            inv_ts.append(t)
            inv_vals.append(pos[product])

    if not inv_ts and trades_df is not None and not trades_df.empty:
        ptrades = trades_df[trades_df["symbol"] == product].sort_values("timestamp")
        running_pos = 0
        for _, row in ptrades.iterrows():
            if row.get("buyer") == "SUBMISSION":
                running_pos += row["quantity"]
            elif row.get("seller") == "SUBMISSION":
                running_pos -= row["quantity"]
            inv_ts.append(row["timestamp"])
            inv_vals.append(running_pos)

    # ── Orders (bid/ask quotes from algo) ──
    algo_bid_ts, algo_bid_px, algo_ask_ts, algo_ask_px = [], [], [], []
    for t in sorted(orders_by_ts.keys()):
        for o in orders_by_ts[t]:
            if o["product"] == product:
                if o["quantity"] > 0:
                    algo_bid_ts.append(t)
                    algo_bid_px.append(o["price"])
                elif o["quantity"] < 0:
                    algo_ask_ts.append(t)
                    algo_ask_px.append(o["price"])

    has_inventory = len(inv_ts) > 0
    has_pnl = pnl.notna().any() and (pnl != 0).any()
    n_rows = 1 + int(has_inventory) + int(has_pnl)
    row_heights = [0.5]
    if has_inventory:
        row_heights.append(0.2)
    if has_pnl:
        row_heights.append(0.3)

    subtitles = [f"{product} — Price & Spread"]
    if has_inventory:
        subtitles.append("Inventory (q)")
    if has_pnl:
        subtitles.append("PnL & Drawdown")

    fig = make_subplots(
        rows=n_rows, cols=1, shared_xaxes=True,
        vertical_spacing=0.04, row_heights=row_heights,
        subplot_titles=subtitles,
    )

    # ─── Row 1: Price & Spread Ribbon ──────────────────────────────────────────

    fig.add_trace(go.Scatter(
        x=ts, y=best_ask, mode="lines", name="Best Ask",
        line=dict(color="rgba(255,77,106,0.3)", width=0),
        showlegend=False, hoverinfo="skip",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=ts, y=best_bid, mode="lines", name="Spread Ribbon",
        line=dict(color="rgba(0,229,160,0.3)", width=0),
        fill="tonexty", fillcolor="rgba(124,92,252,0.07)",
        showlegend=True, hoverinfo="skip",
    ), row=1, col=1)

    if algo_ask_ts:
        fig.add_trace(go.Scatter(
            x=algo_ask_ts, y=algo_ask_px, mode="lines",
            name="My Ask Quote", line=dict(color=ASK_COLOR, width=1, dash="dot"),
        ), row=1, col=1)
    if algo_bid_ts:
        fig.add_trace(go.Scatter(
            x=algo_bid_ts, y=algo_bid_px, mode="lines",
            name="My Bid Quote", line=dict(color=BID_COLOR, width=1, dash="dot"),
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=ts, y=mid, mode="lines", name="Mid Price",
        line=dict(color=MID_COLOR, width=2),
    ), row=1, col=1)

    if buy_ts:
        fig.add_trace(go.Scatter(
            x=buy_ts, y=buy_px, mode="markers", name="BUY",
            marker=dict(color=BUY_COLOR, size=9, symbol="triangle-up",
                        line=dict(color="#fff", width=1)),
        ), row=1, col=1)
    if sell_ts:
        fig.add_trace(go.Scatter(
            x=sell_ts, y=sell_px, mode="markers", name="SELL",
            marker=dict(color=SELL_COLOR, size=9, symbol="triangle-down",
                        line=dict(color="#fff", width=1)),
        ), row=1, col=1)

    # ─── Row 2: Inventory ──────────────────────────────────────────────────────
    current_row = 2
    if has_inventory:
        fig.add_trace(go.Scatter(
            x=inv_ts, y=inv_vals, mode="lines+markers", name="Inventory",
            line=dict(color=INVENTORY_COLOR, width=2),
            marker=dict(size=3, color=INVENTORY_COLOR),
            fill="tozeroy", fillcolor="rgba(124,92,252,0.10)",
        ), row=current_row, col=1)

        q_max = max(abs(v) for v in inv_vals) if inv_vals else 20
        limit_val = max(q_max, 20)
        fig.add_hline(y=0, line=dict(color=ZERO_LINE, width=1, dash="dash"),
                      row=current_row, col=1)
        fig.add_hline(y=limit_val, line=dict(color=ASK_COLOR, width=1, dash="dot"),
                      row=current_row, col=1, annotation_text=f"Q_max={limit_val}",
                      annotation_position="top left",
                      annotation_font=dict(color=ASK_COLOR, size=9))
        fig.add_hline(y=-limit_val, line=dict(color=BID_COLOR, width=1, dash="dot"),
                      row=current_row, col=1, annotation_text=f"-Q_max={-limit_val}",
                      annotation_position="bottom left",
                      annotation_font=dict(color=BID_COLOR, size=9))
        current_row += 1

    # ─── Row 3: PnL & Drawdown ─────────────────────────────────────────────────
    if has_pnl:
        pnl_vals = pnl.fillna(0).values
        hwm = np.maximum.accumulate(pnl_vals)
        drawdown = pnl_vals - hwm

        fig.add_trace(go.Scatter(
            x=ts, y=drawdown, mode="lines", name="Drawdown",
            line=dict(color="rgba(255,65,100,0.5)", width=0),
            fill="tozeroy", fillcolor=DRAWDOWN_COLOR,
            hoverinfo="y+name",
        ), row=current_row, col=1)

        fig.add_trace(go.Scatter(
            x=ts, y=pnl_vals, mode="lines", name="PnL",
            line=dict(color=PNL_COLOR, width=2),
        ), row=current_row, col=1)

        fig.add_trace(go.Scatter(
            x=ts, y=hwm, mode="lines", name="High Water Mark",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
        ), row=current_row, col=1)

        fig.add_hline(y=0, line=dict(color=ZERO_LINE, width=1, dash="dash"),
                      row=current_row, col=1)

        if dd_highlight:
            for r in range(1, n_rows + 1):
                fig.add_vrect(
                    x0=dd_highlight["peak_ts"], x1=dd_highlight["trough_ts"],
                    fillcolor="rgba(255,65,100,0.08)", line_width=0,
                    row=r, col=1,
                )
            fig.add_trace(go.Scatter(
                x=[dd_highlight["peak_ts"], dd_highlight["trough_ts"]],
                y=[dd_highlight["peak_pnl"], dd_highlight["trough_pnl"]],
                mode="markers+lines+text",
                marker=dict(
                    size=11, color=["#00e5a0", "#ff4d6a"], symbol="diamond",
                    line=dict(color="#fff", width=1.5),
                ),
                line=dict(color="#ff4d6a", width=1.5, dash="dash"),
                text=[f"Peak: {dd_highlight['peak_pnl']:+,.1f}",
                      f"Trough: {dd_highlight['trough_pnl']:+,.1f}"],
                textposition=["top center", "bottom center"],
                textfont=dict(color="#c0ccd8", size=10, family=FONT),
                name=f"Max DD: {dd_highlight['max_dd']:+,.1f}",
                showlegend=True,
            ), row=current_row, col=1)

    h = 300 + 220 * (n_rows - 1)
    fig.update_layout(
        height=h,
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    for i in range(1, n_rows + 1):
        fig.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, row=i, col=1)
        fig.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, row=i, col=1)

    fig.update_xaxes(title_text="Timestamp", row=n_rows, col=1)

    for ann in fig.layout.annotations:
        ann.font.color = TEXT_COLOR
        ann.font.family = FONT
        ann.font.size = 12

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True})


# ─── Portfolio overview ─────────────────────────────────────────────────────────

PRODUCT_COLORS = [
    "#00bfff", "#e8c547", "#00e5a0", "#ff4d6a",
    "#7c5cfc", "#ff9f43", "#54a0ff", "#ee5a24",
]


def build_portfolio_overview(prices_df, selected_products, sharpe_window):
    product_pnls = {}
    for product in selected_products:
        pdf = prices_df[prices_df["product"] == product].copy().sort_values("timestamp")
        if pdf.empty or "profit_and_loss" not in pdf.columns:
            continue
        pnl_series = pdf.set_index("timestamp")["profit_and_loss"].fillna(0)
        pnl_series = pnl_series.groupby(level=0).last()
        product_pnls[product] = pnl_series

    if not product_pnls:
        return

    all_ts = sorted(set().union(*(s.index for s in product_pnls.values())))
    combined = pd.DataFrame(index=all_ts)
    for product, series in product_pnls.items():
        combined[product] = series.reindex(combined.index).ffill().fillna(0)
    combined["Total"] = combined.sum(axis=1)

    # ─── PnL Over Time ─────────────────────────────────────────────────────────
    fig_pnl = go.Figure()
    for i, product in enumerate(selected_products):
        if product in combined.columns:
            fig_pnl.add_trace(go.Scatter(
                x=combined.index, y=combined[product],
                mode="lines", name=product,
                line=dict(color=PRODUCT_COLORS[i % len(PRODUCT_COLORS)], width=1.5),
            ))

    if len(product_pnls) > 1:
        fig_pnl.add_trace(go.Scatter(
            x=combined.index, y=combined["Total"],
            mode="lines", name="Total",
            line=dict(color="#ffffff", width=2.5),
        ))

    fig_pnl.add_hline(y=0, line=dict(color=ZERO_LINE, width=1, dash="dash"))
    fig_pnl.update_layout(
        title="PnL Over Time",
        height=370,
        **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    fig_pnl.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_text="Timestamp")
    fig_pnl.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_text="PnL")
    st.plotly_chart(fig_pnl, use_container_width=True, config={"displayModeBar": True})

    # ─── Rolling Sharpe & PnL Breakdown side-by-side ───────────────────────────
    col_sharpe, col_breakdown = st.columns([3, 2])

    with col_sharpe:
        total_pnl = combined["Total"]
        returns = total_pnl.diff().fillna(0)
        window = min(sharpe_window, len(returns) - 1) if len(returns) > 1 else 1

        rolling_mean = returns.rolling(window=window, min_periods=window).mean()
        rolling_std = returns.rolling(window=window, min_periods=window).std()
        rolling_sharpe = rolling_mean / rolling_std.replace(0, np.nan)

        fig_sharpe = go.Figure()
        fig_sharpe.add_trace(go.Scatter(
            x=combined.index, y=rolling_sharpe,
            mode="lines", name=f"Rolling Sharpe ({window})",
            line=dict(color="#7c5cfc", width=2),
            fill="tozeroy", fillcolor="rgba(124,92,252,0.08)",
        ))
        fig_sharpe.add_hline(y=0, line=dict(color=ZERO_LINE, width=1, dash="dash"))
        fig_sharpe.update_layout(
            title=f"Rolling Sharpe Ratio (window={window})",
            height=340,
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        )
        fig_sharpe.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_text="Timestamp")
        fig_sharpe.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_text="Sharpe")
        st.plotly_chart(fig_sharpe, use_container_width=True, config={"displayModeBar": True})

    with col_breakdown:
        final_pnls = {}
        for product in selected_products:
            if product in combined.columns:
                final_pnls[product] = combined[product].iloc[-1]

        products_sorted = sorted(final_pnls.keys(), key=lambda p: final_pnls[p])
        values = [final_pnls[p] for p in products_sorted]
        colors = [BID_COLOR if v >= 0 else ASK_COLOR for v in values]

        fig_breakdown = go.Figure()
        fig_breakdown.add_trace(go.Bar(
            y=products_sorted, x=values,
            orientation="h",
            marker=dict(color=colors),
            text=[f"{v:+,.1f}" for v in values],
            textposition="auto",
            textfont=dict(family=FONT, size=11),
        ))
        fig_breakdown.add_vline(x=0, line=dict(color=ZERO_LINE, width=1, dash="dash"))
        fig_breakdown.update_layout(
            title="PnL Per Product",
            height=340,
            **{k: v for k, v in PLOTLY_LAYOUT.items() if k not in ("xaxis", "yaxis")},
        )
        fig_breakdown.update_xaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR, title_text="PnL")
        fig_breakdown.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
        st.plotly_chart(fig_breakdown, use_container_width=True, config={"displayModeBar": True})


# ─── Metric cards ──────────────────────────────────────────────────────────────

def render_metrics(prices_df, trades_df, product):
    pdf = prices_df[prices_df["product"] == product]
    if pdf.empty:
        return None

    pdf = pdf.sort_values("timestamp")
    final_pnl = pdf["profit_and_loss"].iloc[-1] if "profit_and_loss" in pdf.columns else 0
    pnl_vals = pdf["profit_and_loss"].fillna(0).values
    hwm = np.maximum.accumulate(pnl_vals)
    drawdown = pnl_vals - hwm
    max_dd = float(np.min(drawdown))

    dd_info = None
    if max_dd < 0:
        ts_vals = pdf["timestamp"].values
        trough_idx = int(np.argmin(drawdown))
        peak_idx = int(np.argmax(pnl_vals[:trough_idx + 1]))
        dd_info = {
            "peak_ts": float(ts_vals[peak_idx]),
            "peak_pnl": float(pnl_vals[peak_idx]),
            "trough_ts": float(ts_vals[trough_idx]),
            "trough_pnl": float(pnl_vals[trough_idx]),
            "max_dd": max_dd,
        }

    mid_prices = pdf["mid_price"].dropna()
    price_range = f"{mid_prices.min():.0f} – {mid_prices.max():.0f}" if len(mid_prices) > 0 else "—"
    n_timestamps = pdf["timestamp"].nunique()

    n_buys, n_sells = 0, 0
    if trades_df is not None and not trades_df.empty:
        pt = trades_df[trades_df["symbol"] == product]
        n_buys = int((pt["buyer"] == "SUBMISSION").sum())
        n_sells = int((pt["seller"] == "SUBMISSION").sum())

    pnl_class = "green" if final_pnl >= 0 else "red"
    dd_class = "red" if max_dd < 0 else "green"

    cols = st.columns(6)
    cards = [
        ("FINAL PNL", f"{final_pnl:+,.1f}", pnl_class,
         "Cumulative profit &amp; loss at the last timestamp. Positive means net profit, negative means net loss."),
        ("MAX DRAWDOWN", f"{max_dd:+,.1f}", dd_class,
         "Largest peak-to-trough decline in PnL. Measures the worst losing streak from any high-water mark."),
        ("PRICE RANGE", price_range, "",
         "The lowest and highest mid-price observed for this product across all timestamps."),
        ("TIMESTAMPS", f"{n_timestamps:,}", "",
         "Total number of unique time steps in the simulation data for this product."),
        ("BUYS", str(n_buys), "green",
         "Number of trades where your algorithm was the buyer (SUBMISSION appears as buyer)."),
        ("SELLS", str(n_sells), "red",
         "Number of trades where your algorithm was the seller (SUBMISSION appears as seller)."),
    ]
    show_dd = False
    for i, (col, (label, value, cls, tip)) in enumerate(zip(cols, cards)):
        cls_str = f" {cls}" if cls else ""
        card_cls = " dd-clickable" if i == 1 and dd_info else ""
        col.markdown(f"""
        <div class="metric-card{card_cls}">
            <span class="tooltip-text">{tip}</span>
            <div class="label">{label}</div>
            <div class="value{cls_str}">{value}</div>
        </div>
        """, unsafe_allow_html=True)
        if i == 1 and dd_info:
            show_dd = col.checkbox("Show on chart", key=f"show_dd_{product}")

    return dd_info if show_dd else None


# ─── Main ──────────────────────────────────────────────────────────────────────

st.markdown('<div class="header-glow">BACKTESTER DASHBOARD</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Data Upload")
    st.markdown(
        '<span style="color:#556677;font-size:0.75rem;letter-spacing:0.1em;">', 
        unsafe_allow_html=True,
    )

    csv_file = st.file_uploader("Price CSV (.csv)", type=["csv"], key="csv")
    trades_csv_file = st.file_uploader("Trades CSV (.csv) — optional", type=["csv"], key="trades_csv")
    log_file = st.file_uploader("Backtest Log (.log)", type=["log", "txt"], key="log")

    st.markdown("---")
    st.markdown(
        '<span style="color:#556677;font-size:0.7rem;letter-spacing:0.1em;">'
        'Supports IMC Prosperity format:<br>'
        '• CSV: day;timestamp;product;...;mid_price;profit_and_loss<br>'
        '• LOG: Sandbox logs + Activities log + Trade History</span>',
        unsafe_allow_html=True,
    )


prices_df = None
trades_df = None
orders_by_ts = {}
positions_by_ts = {}

if log_file is not None:
    raw = log_file.read()
    with st.spinner("Parsing backtester log — this may take a moment for large files..."):
        activities_df, trades_list, orders_by_ts, positions_by_ts = parse_log_file(raw)
    if activities_df is not None and not activities_df.empty:
        prices_df = activities_df
    if trades_list:
        trades_df = pd.DataFrame(trades_list)

if csv_file is not None:
    csv_prices = parse_prices_csv(csv_file.read())
    if prices_df is None:
        prices_df = csv_prices
    else:
        prices_df = pd.concat([prices_df, csv_prices], ignore_index=True)

if trades_csv_file is not None:
    trades_csv_raw = trades_csv_file.read().decode("utf-8")
    trades_csv_df = pd.read_csv(io.StringIO(trades_csv_raw), sep=";")
    for col in ("price", "quantity"):
        if col in trades_csv_df.columns:
            trades_csv_df[col] = pd.to_numeric(trades_csv_df[col], errors="coerce")
    if "symbol" not in trades_csv_df.columns and "product" in trades_csv_df.columns:
        trades_csv_df = trades_csv_df.rename(columns={"product": "symbol"})
    if trades_df is None:
        trades_df = trades_csv_df
    else:
        trades_df = pd.concat([trades_df, trades_csv_df], ignore_index=True)

if prices_df is not None and not prices_df.empty:
    products = sorted(prices_df["product"].unique())

    with st.sidebar:
        st.markdown("### Products")
        selected_products = st.multiselect(
            "Select products to analyze",
            products,
            default=products,
        )

        st.markdown("### Day Filter")
        if "day" in prices_df.columns:
            days = sorted(prices_df["day"].unique())
            selected_days = st.multiselect("Select days", days, default=days)
            prices_df = prices_df[prices_df["day"].isin(selected_days)]
        else:
            selected_days = None

        st.markdown("### Analytics")
        sharpe_window = st.slider(
            "Rolling Sharpe window",
            min_value=10, max_value=500, value=100, step=10,
        )

    if not selected_products:
        st.info("Select at least one product from the sidebar.")
    else:
        build_portfolio_overview(prices_df, selected_products, sharpe_window)

        for product in selected_products:
            st.markdown(f"---")
            dd_highlight = render_metrics(prices_df, trades_df, product)
            build_charts(prices_df, trades_df, product, orders_by_ts, positions_by_ts, dd_highlight=dd_highlight)

else:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                min-height:55vh;opacity:0.7;">
        <div style="font-size:4rem;margin-bottom:16px;">📊</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;color:#556677;
                    letter-spacing:0.15em;text-align:center;">
            Upload a <span style="color:#e8c547;">.csv</span> price file or
            <span style="color:#00e5a0;">.log</span> backtester file<br>
            to begin analysis
        </div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:0.75rem;color:#334455;
                    letter-spacing:0.1em;margin-top:12px;text-align:center;">
            Use the sidebar file uploaders on the left
        </div>
    </div>
    """, unsafe_allow_html=True)
