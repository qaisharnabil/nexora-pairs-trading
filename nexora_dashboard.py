import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nexora Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 30 seconds (no extra packages required)
st.markdown('<meta http-equiv="refresh" content="30">', unsafe_allow_html=True)

# ── Palette ───────────────────────────────────────────────────────────────────
BG     = "#0d1117"
CARD   = "#161b22"
BORDER = "#30363d"
GREEN  = "#3fb950"
RED    = "#f85149"
BLUE   = "#58a6ff"
YELLOW = "#e3b341"
TEXT   = "#c9d1d9"
MUTED  = "#8b949e"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
.stApp, .main, div[data-testid="stAppViewContainer"],
div[data-testid="stHeader"], div[data-testid="stToolbar"] {{
    background-color: {BG} !important;
}}
.kpi-card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px 10px;
    text-align: center;
    height: 90px;
}}
.kpi-val {{ font-size: 24px; font-weight: 700; font-family: "Courier New", monospace; }}
.kpi-lbl {{ font-size: 11px; color: {MUTED}; margin-top: 5px; letter-spacing: .5px; text-transform: uppercase; }}
header, footer, #MainMenu {{ visibility: hidden !important; }}
div[data-testid="stDataFrame"] * {{ color: {TEXT} !important; }}
div[data-testid="stDataFrame"] {{ background: {CARD}; }}
</style>
""", unsafe_allow_html=True)

# ── Data ──────────────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nexora_trades.csv")
REQUIRED_COLS = [
    "timestamp", "pair", "tf", "direction",
    "entry_spread", "exit_spread", "pnl_poin",
    "pnl_dollar", "reason", "hours_held",
]


@st.cache_data(ttl=30)
def load_data() -> pd.DataFrame:
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=REQUIRED_COLS)
    df = pd.read_csv(CSV_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


# ── KPI calculations ──────────────────────────────────────────────────────────
def compute_kpis(df: pd.DataFrame) -> dict:
    pnl    = df["pnl_dollar"]
    wins   = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    equity = pnl.cumsum()
    dd     = equity - equity.cummax()
    std    = pnl.std()

    sharpe = pnl.mean() / std * np.sqrt(len(pnl)) if std and std > 0 else 0.0
    rr     = abs(wins.mean() / losses.mean()) if len(wins) and len(losses) and losses.mean() != 0 else 0.0

    return {
        "total_pnl": pnl.sum(),
        "win_rate":  len(wins) / len(pnl) * 100 if len(pnl) else 0.0,
        "sharpe":    sharpe,
        "max_dd":    dd.min(),
        "avg_win":   wins.mean()   if len(wins)   else 0.0,
        "avg_loss":  losses.mean() if len(losses) else 0.0,
        "rr_ratio":  rr,
    }


# ── Plotly dark-theme helper (avoids all duplicate-kwarg errors) ───────────────
def dark_layout(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    """Apply dark theme once via a single update_layout + axis helpers.
    All axis-specific props use update_xaxes / update_yaxes to prevent
    any duplicate keyword argument errors."""
    fig.update_layout(
        plot_bgcolor=CARD,
        paper_bgcolor=CARD,
        font=dict(color=TEXT, family="Courier New, monospace"),
        title=dict(text=title, font=dict(color=TEXT, size=15)),
        height=height,
        margin=dict(l=54, r=54, t=58, b=42),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT),
            orientation="h",
            y=1.08,
        ),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER)
    fig.update_yaxes(gridcolor=BORDER, linecolor=BORDER, zerolinecolor=BORDER)
    return fig


# ── Chart 1 : Equity curve + drawdown + rolling Sharpe ───────────────────────
def chart_equity(df: pd.DataFrame) -> go.Figure:
    pnl    = df["pnl_dollar"]
    equity = pnl.cumsum()
    dd     = equity - equity.cummax()
    roll_sharpe = pnl.rolling(20).apply(
        lambda x: x.mean() / x.std() * np.sqrt(20) if x.std() > 0 else 0.0,
        raw=True,
    )

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.68, 0.32],
        vertical_spacing=0.04,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
    )

    # Equity curve (primary y, row 1)
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"], y=equity,
            name="Equity ($)",
            line=dict(color=BLUE, width=2),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.07)",
        ),
        row=1, col=1, secondary_y=False,
    )

    # Rolling 20-trade Sharpe (secondary y, row 1)
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"], y=roll_sharpe,
            name="Rolling Sharpe (20)",
            line=dict(color=YELLOW, width=1, dash="dot"),
            opacity=0.9,
        ),
        row=1, col=1, secondary_y=True,
    )

    # Drawdown (row 2)
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"], y=dd,
            name="Drawdown",
            line=dict(color=RED, width=1),
            fill="tozeroy", fillcolor="rgba(248,81,73,0.18)",
        ),
        row=2, col=1,
    )

    dark_layout(fig, title="Equity Curve  ·  Drawdown  ·  Rolling Sharpe (20)", height=520)

    # Per-axis titles/props — use update_yaxes with row/col/secondary_y
    # (no update_layout axis keys → zero duplicate-kwarg risk)
    fig.update_yaxes(title_text="Equity ($)", row=1, col=1, secondary_y=False)
    fig.update_yaxes(
        title_text="Sharpe", row=1, col=1, secondary_y=True,
        showgrid=False, zeroline=True, zerolinecolor=BORDER,
    )
    fig.update_yaxes(title_text="Drawdown ($)", row=2, col=1)

    return fig


# ── Chart 2 : PnL breakdown ───────────────────────────────────────────────────
def chart_breakdown(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=["By Pair", "By Timeframe", "By Direction"],
        horizontal_spacing=0.10,
    )

    for c, col in enumerate(["pair", "tf", "direction"], start=1):
        grp = df.groupby(col, sort=False)["pnl_dollar"].sum().reset_index()
        grp.columns = [col, "pnl"]
        grp = grp.sort_values("pnl", ascending=False)
        colors = [GREEN if v >= 0 else RED for v in grp["pnl"]]

        fig.add_trace(
            go.Bar(
                x=grp[col], y=grp["pnl"],
                marker_color=colors,
                showlegend=False,
                text=[f"${v:,.0f}" for v in grp["pnl"]],
                textposition="outside",
                textfont=dict(color=TEXT, size=11),
            ),
            row=1, col=c,
        )

    dark_layout(fig, title="PnL Breakdown", height=360)
    return fig


# ── Chart 3 : PnL distribution histogram ─────────────────────────────────────
def chart_distribution(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    for subset, color, label in (
        (df[df["pnl_dollar"] > 0]["pnl_dollar"], GREEN, "Wins"),
        (df[df["pnl_dollar"] < 0]["pnl_dollar"], RED,   "Losses"),
    ):
        if not subset.empty:
            fig.add_trace(go.Histogram(
                x=subset, name=label,
                marker_color=color, opacity=0.75, nbinsx=30,
            ))

    fig.add_vline(x=0, line_color=MUTED, line_dash="dash", line_width=1)
    fig.update_layout(barmode="overlay")
    dark_layout(fig, title="PnL Distribution", height=360)
    fig.update_xaxes(title_text="PnL ($)")
    fig.update_yaxes(title_text="Count")
    return fig


# ── Chart 4 : Win rate per pair ───────────────────────────────────────────────
def chart_winrate(df: pd.DataFrame) -> go.Figure:
    wr = (
        df.groupby("pair")["pnl_dollar"]
        .apply(lambda x: (x > 0).mean() * 100)
        .reset_index()
    )
    wr.columns = ["pair", "wr"]
    wr = wr.sort_values("wr", ascending=False)
    colors = [GREEN if v >= 50 else RED for v in wr["wr"]]

    fig = go.Figure(go.Bar(
        x=wr["pair"], y=wr["wr"],
        marker_color=colors,
        text=[f"{v:.1f}%" for v in wr["wr"]],
        textposition="outside",
        textfont=dict(color=TEXT),
    ))
    fig.add_hline(
        y=50, line_color=MUTED, line_dash="dash", line_width=1,
        annotation_text="50 %", annotation_font_color=MUTED,
    )
    dark_layout(fig, title="Win Rate per Pair", height=360)
    fig.update_yaxes(title_text="Win Rate (%)", range=[0, 108])
    return fig


# ── Trade log with PnL color-coding ──────────────────────────────────────────
def styled_trade_log(df: pd.DataFrame):
    out = df[REQUIRED_COLS].copy()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    out = out.sort_values("timestamp", ascending=False).head(200).reset_index(drop=True)

    def pnl_color(val):
        if not isinstance(val, (int, float, np.floating)):
            return ""
        if val > 0:
            return f"color: {GREEN}; font-weight: 600"
        if val < 0:
            return f"color: {RED}; font-weight: 600"
        return f"color: {TEXT}"

    styler = out.style
    # pandas ≥2.1 uses .map(); older versions use .applymap()
    try:
        styler = styler.map(pnl_color, subset=["pnl_dollar", "pnl_poin"])
    except AttributeError:
        styler = styler.applymap(pnl_color, subset=["pnl_dollar", "pnl_poin"])

    return styler.set_properties(**{
        "background-color": CARD,
        "color": TEXT,
        "font-family": "Courier New, monospace",
        "font-size": "12px",
    })


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Header
    st.markdown(f"""
    <div style="border-bottom:1px solid {BORDER}; padding:14px 0 10px; margin-bottom:20px">
      <span style="color:{BLUE}; font-size:26px; font-weight:700;
                   font-family:'Courier New',monospace; letter-spacing:2px">
        ⚡ NEXORA TRADING DASHBOARD
      </span>
      <span style="color:{MUTED}; font-size:12px; margin-left:18px; font-family:monospace">
        auto-refresh every 30 s
      </span>
    </div>""", unsafe_allow_html=True)

    df = load_data()

    if df.empty:
        st.warning(
            f"No data found — place `nexora_trades.csv` in `{os.path.dirname(CSV_PATH)}`.\n\n"
            f"Expected columns: {', '.join(REQUIRED_COLS)}"
        )
        return

    kpis = compute_kpis(df)

    # ── KPI cards ──────────────────────────────────────────────────────────────
    st.markdown("#### Key Performance Indicators")
    kpi_specs = [
        ("Total PnL",    f"${kpis['total_pnl']:,.2f}",  kpis["total_pnl"] >= 0),
        ("Win Rate",     f"{kpis['win_rate']:.1f}%",     kpis["win_rate"] >= 50),
        ("Sharpe Ratio", f"{kpis['sharpe']:.2f}",        kpis["sharpe"] >= 1),
        ("Max Drawdown", f"${kpis['max_dd']:,.2f}",      False),
        ("Avg Win",      f"${kpis['avg_win']:,.2f}",     True),
        ("Avg Loss",     f"${kpis['avg_loss']:,.2f}",    False),
        ("R:R Ratio",    f"{kpis['rr_ratio']:.2f}",      kpis["rr_ratio"] >= 1),
    ]

    for col, (label, val, good) in zip(st.columns(7), kpi_specs):
        color = GREEN if good else RED
        col.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-val" style="color:{color}">{val}</div>
          <div class="kpi-lbl">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Equity curve ───────────────────────────────────────────────────────────
    st.plotly_chart(chart_equity(df), use_container_width=True)

    # ── PnL breakdown ──────────────────────────────────────────────────────────
    st.plotly_chart(chart_breakdown(df), use_container_width=True)

    # ── Distribution + win rate ────────────────────────────────────────────────
    c1, c2 = st.columns(2)
    c1.plotly_chart(chart_distribution(df), use_container_width=True)
    c2.plotly_chart(chart_winrate(df),      use_container_width=True)

    # ── Trade log ──────────────────────────────────────────────────────────────
    n      = len(df)
    last_t = df["timestamp"].max().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"#### Trade Log &nbsp;"
        f"<span style='color:{MUTED};font-size:13px'>{n} trades · last: {last_t}</span>",
        unsafe_allow_html=True,
    )
    st.dataframe(styled_trade_log(df), use_container_width=True, height=440)

    # Footer
    st.markdown(f"""
    <div style="text-align:right; color:{MUTED}; font-size:11px;
                margin-top:14px; font-family:monospace">
      nexora_dashboard.py · Streamlit + Plotly
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()