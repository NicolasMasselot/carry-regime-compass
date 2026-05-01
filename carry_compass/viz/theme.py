import plotly.graph_objects as go

BG_MAIN = "#0a0a0a"
BG_PANEL = "#141414"
BG_PANEL_ALT = "#111111"
BORDER = "#2a2a2a"
GRID = "#1f1f1f"
TEXT_PRIMARY = "#e8e8e8"
TEXT_SECONDARY = "#888888"

ASSET_CLASS_COLORS = {
    "fx_carry": "#2563eb",
    "rates": "#ea580c",
    "credit": "#16a34a",
    "equity": "#dc2626",
    "commodity": "#7c3aed",
}

ASSET_CLASS_COLORS_DARK = {
    "fx_carry": "#60a5fa",
    "rates": "#fb923c",
    "credit": "#4ade80",
    "equity": "#f87171",
    "commodity": "#a78bfa",
}

REGIME_COLORS = {
    "Risk-On": "#15803d",
    "Mid-Cycle": "#0369a1",
    "Late-Cycle": "#b45309",
    "Deleveraging": "#b91c1c",
}

REGIME_COLORS_DARK = {
    "Risk-On": "#16a34a",
    "Mid-Cycle": "#0ea5e9",
    "Late-Cycle": "#d99521",
    "Deleveraging": "#c73737",
}

POSITIVE = "#22c55e"
NEGATIVE = "#ef4444"
WARNING = "#d99521"

REGIME_DESCRIPTIONS = {
    "Risk-On": (
        "Cross-asset carry is rich while realized volatility is compressed. "
        "The environment is broadly friendly to carry exposure."
    ),
    "Mid-Cycle": "Carry and volatility sit close to long-run averages.",
    "Late-Cycle": (
        "Carry is still positive, but volatility pressure is building. "
        "Crowded carry trades deserve closer monitoring."
    ),
    "Deleveraging": (
        "Volatility is elevated and carry is weak. The dashboard is flagging "
        "a risk-off deleveraging state."
    ),
}


def apply_dark_theme(fig: go.Figure) -> go.Figure:
    """Apply the dark institutional dashboard theme to a Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_PANEL,
        plot_bgcolor=BG_MAIN,
        font={"color": TEXT_PRIMARY, "family": "Inter, system-ui, sans-serif", "size": 12},
        margin={"l": 12, "r": 12, "t": 12, "b": 12},
        legend={
            "bgcolor": "rgba(0,0,0,0)",
            "bordercolor": BORDER,
            "borderwidth": 1,
            "font": {"color": TEXT_SECONDARY, "size": 11},
        },
    )
    fig.update_xaxes(
        color=TEXT_SECONDARY,
        gridcolor=GRID,
        linecolor=BORDER,
        zerolinecolor=BORDER,
        title_font={"color": TEXT_SECONDARY, "size": 11},
        tickfont={"family": "JetBrains Mono, IBM Plex Mono, monospace", "size": 11},
    )
    fig.update_yaxes(
        color=TEXT_SECONDARY,
        gridcolor=GRID,
        linecolor=BORDER,
        zerolinecolor=BORDER,
        title_font={"color": TEXT_SECONDARY, "size": 11},
        tickfont={"family": "JetBrains Mono, IBM Plex Mono, monospace", "size": 11},
    )
    return fig
