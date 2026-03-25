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
        padding: 14px 18px; text-align: center; }
    .metric-card .label { font-size: 0.7rem; color: #556677; letter-spacing: 0.15em;
        text-transform: uppercase; font-family: 'JetBrains Mono', monospace; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700;
        font-family: 'JetBrains Mono', monospace; color: #e8c547; margin-top: 4px; }
    .metric-card .value.green { color: #00e5a0; }
    .metric-card .value.red { color: #ff4d6a; }
    div[data-testid="stFileUploader"] label { color: #c0ccd8 !important;
        font-family: 'JetBrains Mono', monospace !important; }
    .stSelectbox label, .stMultiSelect label { color: #c0ccd8 !important;
        font-family: 'JetBrains Mono', monospace !important; }
</style>
""", unsafe_allow_html=True)


# ─── Parsers ───────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def parse_prices_csv(file_bytes: bytes) -> pd.DataFrame:
    text = file_bytes.decode("utf-8")
    df = pd.read_csv(io.StringIO(text), sep=";")
    for col in df.columns:
        if "price" in col or "volume" in col or col in ("mid_price", "profit_and_loss"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def parse_log_file(file_bytes: bytes):
    text = file_bytes.decode("utf-8")

    activities_df = None
    trades_list = []

    act_match = text.find("Activities log:\n")
    trade_match = text.find("Trade History:\n")

    if act_match != -1:
        act_start = act_match + len("Activities log:\n")
        act_end = trade_match if trade_match != -1 else len(text)
        act_text = text[act_start:act_end].strip()
        if act_text:
            activities_df = pd.read_csv(io.StringIO(act_text), sep=";")
            for col in activities_df.columns:
                if "price" in col or "volume" in col or col in ("mid_price", "profit_and_loss"):
                    activities_df[col] = pd.to_numeric(activities_df[col], errors="coerce")

    if trade_match != -1:
        trade_start = trade_match + len("Trade History:\n")
        trade_text = text[trade_start:].strip()
        trade_text = re.sub(r",(\s*[}\]])", r"\1", trade_text)
        try:
            trades_list = json.loads(trade_text)
        except json.JSONDecodeError:
            trades_list = []

    sandbox_entries = []
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
            stripped = line.strip()
            if stripped == "{" or (stripped.startswith("{") and '"sandboxLog"' in stripped):
                in_block = True
                block = stripped
            elif in_block:
                block += stripped
                if stripped == "}":
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

def build_charts(prices_df, trades_df, product, orders_by_ts, positions_by_ts):
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


# ─── Metric cards ──────────────────────────────────────────────────────────────

def render_metrics(prices_df, trades_df, product):
    pdf = prices_df[prices_df["product"] == product]
    if pdf.empty:
        return

    final_pnl = pdf["profit_and_loss"].iloc[-1] if "profit_and_loss" in pdf.columns else 0
    pnl_vals = pdf["profit_and_loss"].fillna(0).values
    hwm = np.maximum.accumulate(pnl_vals)
    max_dd = float(np.min(pnl_vals - hwm))
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
        ("FINAL PNL", f"{final_pnl:+,.1f}", pnl_class),
        ("MAX DRAWDOWN", f"{max_dd:+,.1f}", dd_class),
        ("PRICE RANGE", price_range, ""),
        ("TIMESTAMPS", f"{n_timestamps:,}", ""),
        ("BUYS", str(n_buys), "green"),
        ("SELLS", str(n_sells), "red"),
    ]
    for col, (label, value, cls) in zip(cols, cards):
        cls_str = f" {cls}" if cls else ""
        col.markdown(f"""
        <div class="metric-card">
            <div class="label">{label}</div>
            <div class="value{cls_str}">{value}</div>
        </div>
        """, unsafe_allow_html=True)


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

    if not selected_products:
        st.info("Select at least one product from the sidebar.")
    else:
        for product in selected_products:
            st.markdown(f"---")
            render_metrics(prices_df, trades_df, product)
            build_charts(prices_df, trades_df, product, orders_by_ts, positions_by_ts)

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
