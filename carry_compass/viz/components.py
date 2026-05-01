from __future__ import annotations

import datetime as dt
import html
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from carry_compass.cache import PriceCache
from carry_compass.config.schema import AppConfig, AssetClass
from carry_compass.viz.theme import (
    ASSET_CLASS_COLORS_DARK,
    BG_PANEL,
    BORDER,
    NEGATIVE,
    POSITIVE,
    REGIME_COLORS_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    WARNING,
    apply_dark_theme,
)


def _regime_label(value: object) -> str:
    return str(getattr(value, "value", value))


def _asset_class_label(value: object) -> str:
    if isinstance(value, AssetClass):
        value = value.value
    return str(value).replace("_", " ").upper()


def _asset_class_short(value: object) -> str:
    labels = {
        "fx_carry": "FX",
        "commodity": "CMDTY",
        "equity": "EQTY",
        "credit": "CREDIT",
        "rates": "RATES",
    }
    return labels.get(str(value), str(value).upper())


def _format_pct(value: float, decimals: int = 1, signed: bool = False) -> str:
    sign = "+" if signed else ""
    return f"{value * 100:{sign}.{decimals}f}%"


def _format_signed(value: float, decimals: int = 2) -> str:
    return f"{value:+.{decimals}f}"


def _signed_class(value: float) -> str:
    return "crc-pos" if value >= 0 else "crc-neg"


def _status(fetch_results: dict[str, Any]) -> tuple[str, str]:
    total = len(fetch_results)
    stale = sum(1 for result in fetch_results.values() if getattr(result, "stale", False))
    if total == 0 or stale == total:
        return "OFFLINE", NEGATIVE
    if stale > 0:
        return "DELAYED", WARNING
    return "LIVE", POSITIVE


def _cache_size_mb(cache: PriceCache) -> float:
    path = Path(cache.sqlite_path)
    if not path.exists():
        return 0.0
    return path.stat().st_size / (1024 * 1024)


def _latest_fetch_time(fetch_results: dict[str, Any]) -> str:
    if not fetch_results:
        return "--:--:--"
    return dt.datetime.now(dt.UTC).strftime("%H:%M:%S")


def _latest_panel() -> pd.DataFrame:
    value = st.session_state.get("crc_latest_panel")
    if isinstance(value, pd.DataFrame):
        return value
    return pd.DataFrame()


def render_topbar(fetch_results: dict[str, Any], last_update: dt.datetime) -> None:
    """Render the sticky command-center header."""
    label, color = _status(fetch_results)
    timestamp = last_update.astimezone(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.markdown(
        f"""
        <div class="crc-topbar">
            <div class="crc-brand">CARRY REGIME COMPASS</div>
            <div class="crc-clock">{html.escape(timestamp)}</div>
            <div class="crc-status">
                <span class="crc-dot" style="background:{color};"></span>
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_strip(
    regime: str,
    carry_z: float,
    vol_z: float,
    last_transition: str,
) -> None:
    """Render the four primary regime KPIs."""
    color = REGIME_COLORS_DARK.get(regime, TEXT_SECONDARY)
    kpis = [
        (
            "Regime",
            f'<span class="crc-dot" style="background:{color};"></span>{html.escape(regime)}',
            "",
            "crc-regime-value",
        ),
        (
            "Carry z-score",
            html.escape(_format_signed(carry_z)),
            "crc-pos" if carry_z >= 0 else "crc-neg",
            "",
        ),
        (
            "Vol z-score",
            html.escape(_format_signed(vol_z)),
            "crc-neg" if vol_z >= 0 else "crc-pos",
            "",
        ),
        ("Last transition", html.escape(last_transition), "", "crc-value-small"),
    ]
    cards = []
    for label, value, value_class, extra_class in kpis:
        cards.append(
            f'<div class="crc-kpi">'
            f'<div class="crc-label">{html.escape(label)}</div>'
            f'<div class="crc-value {value_class} {extra_class}">{value}</div>'
            f"</div>"
        )
    st.markdown(f'<div class="crc-kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_scatter_dark(latest: pd.DataFrame, centroid_trail: pd.DataFrame) -> None:
    """Render the carry/volatility map in a dark Plotly theme."""
    fig = px.scatter(
        latest,
        x="carry",
        y="vol",
        color="asset_class",
        color_discrete_map=ASSET_CLASS_COLORS_DARK,
        hover_name="asset",
        hover_data={
            "date": "|%Y-%m-%d",
            "asset": False,
            "asset_class": True,
            "ratio": ":.2f",
            "carry": ":.4f",
            "vol": ":.3f",
        },
    )
    fig.update_traces(marker={"size": 12, "line": {"color": BG_PANEL, "width": 1}})

    if not centroid_trail.empty:
        trail = centroid_trail.reset_index().rename(columns={"index": "date"})
        denom = max(len(trail) - 1, 1)
        marker_sizes = [3 + 5 * (idx / denom) for idx in range(len(trail))]
        fig.add_trace(
            go.Scatter(
                x=trail["carry_med"],
                y=trail["vol_med"],
                mode="lines+markers",
                name="Centroid trail",
                line={"color": "rgba(255,255,255,0.35)", "dash": "dot", "width": 1.5},
                marker={"size": marker_sizes, "color": "rgba(255,255,255,0.35)"},
                customdata=trail["date"],
                hovertemplate="Centroid %{customdata|%Y-%m-%d}<br>"
                "Carry=%{x:.4f}<br>Vol=%{y:.3f}<extra></extra>",
            )
        )
        today = trail.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[today["carry_med"]],
                y=[today["vol_med"]],
                mode="markers",
                name="Centroid today",
                marker={"size": 16, "color": TEXT_PRIMARY, "symbol": "x", "line": {"width": 2}},
                customdata=[today["date"]],
                hovertemplate="Today %{customdata|%Y-%m-%d}<br>"
                "Carry=%{x:.4f}<br>Vol=%{y:.3f}<extra></extra>",
            )
        )

    fig.update_layout(
        height=540,
        hovermode="closest",
        legend={
            "orientation": "v",
            "yanchor": "top",
            "y": 0.98,
            "xanchor": "right",
            "x": 0.99,
            "bgcolor": "rgba(20,20,20,0.55)",
            "bordercolor": BORDER,
            "borderwidth": 1,
        },
        xaxis_title="CARRY (ANNUALIZED)",
        yaxis_title="REALIZED VOL (30D ANN.)",
    )
    fig.update_xaxes(tickformat=".0%", zeroline=True)
    fig.update_yaxes(tickformat=".0%", zeroline=True)
    apply_dark_theme(fig)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_ranking_table(latest: pd.DataFrame) -> None:
    """Render a dense HTML ranking table with ratio sparkbars."""
    if latest.empty:
        st.caption("No current asset data available.")
        return

    show = latest.sort_values("ratio", ascending=False).copy()
    max_abs = max(show["ratio"].abs().max(), 1.0)
    rows = []
    for _, row in show.iterrows():
        ratio = float(row["ratio"])
        carry = float(row["carry"])
        vol = float(row["vol"])
        color = POSITIVE if ratio >= 0 else NEGATIVE
        width = max(6.0, min(100.0, abs(ratio) / max_abs * 100.0))
        asset_class = str(row["asset_class"])
        class_color = ASSET_CLASS_COLORS_DARK.get(asset_class, TEXT_SECONDARY)
        ratio_label = _format_signed(ratio)
        if abs(ratio) >= 19.999:
            ratio_label = f"{ratio_label}*"
        rows.append(
            f"<tr>"
            f'<td>{html.escape(str(row["asset"]))}</td>'
            f'<td>{pd.Timestamp(row["date"]).strftime("%m-%d")}</td>'
            f"<td>"
            f'<span class="crc-class">'
            f'<span class="crc-mini-dot" style="background:{class_color};"></span>'
            f"{html.escape(_asset_class_short(asset_class))}"
            f"</span>"
            f"</td>"
            f'<td class="crc-num {_signed_class(carry)}">'
            f"{html.escape(_format_pct(carry, 2, True))}"
            f"</td>"
            f'<td class="crc-num">{html.escape(_format_pct(vol, 1))}</td>'
            f'<td class="crc-ratio-cell">'
            f'<span class="crc-sparkbar" style="width:{width:.1f}%; background:{color};"></span>'
            f'<span class="crc-ratio-text {_signed_class(ratio)}">'
            f"{html.escape(ratio_label)}"
            f"</span>"
            f"</td>"
            f"</tr>"
        )

    st.markdown(
        f'<div class="crc-ranking-wrap">'
        f'<table class="crc-table">'
        f"<thead><tr>"
        f"<th>Asset</th>"
        f"<th>A/O</th>"
        f"<th>Class</th>"
        f'<th class="crc-num">Carry</th>'
        f'<th class="crc-num">Vol</th>'
        f'<th class="crc-num">C/V</th>'
        f"</tr></thead>"
        f'<tbody>{"".join(rows)}</tbody>'
        f"</table>"
        f'<div class="crc-subvalue" style="padding:6px 8px;">* C/V clipped at +/-20.</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_regime_timeline(regimes: pd.DataFrame) -> None:
    """Render a 120-day one-line regime history."""
    if regimes.empty:
        st.caption("No regime history available.")
        return

    recent = regimes.tail(120).copy()
    regime_col = "regime_smoothed" if "regime_smoothed" in recent.columns else "regime"
    recent["_label"] = recent[regime_col].map(_regime_label)
    dates = pd.DatetimeIndex(recent.index)
    labels = list(recent["_label"])

    fig = go.Figure()
    start_idx = 0
    for idx in range(1, len(labels) + 1):
        if idx < len(labels) and labels[idx] == labels[start_idx]:
            continue
        label = labels[start_idx]
        start = dates[start_idx]
        end = dates[idx - 1]
        if start == end:
            end = end + pd.Timedelta(days=1)
        fig.add_trace(
            go.Scatter(
                x=[start, end],
                y=[1, 1],
                mode="lines",
                line={"color": REGIME_COLORS_DARK.get(label, TEXT_SECONDARY), "width": 18},
                name=label,
                hovertemplate=f"{html.escape(label)}<br>%{{x|%Y-%m-%d}}<extra></extra>",
                showlegend=label not in [trace.name for trace in fig.data],
            )
        )
        if idx < len(labels):
            transition_date = dates[idx]
            fig.add_vline(
                x=transition_date,
                line={"color": "rgba(255,255,255,0.5)", "width": 1},
            )
            fig.add_annotation(
                x=transition_date,
                y=1.35,
                text=labels[idx],
                showarrow=False,
                font={"size": 10, "color": TEXT_SECONDARY},
                textangle=-35,
            )
        start_idx = idx

    fig.update_layout(
        height=96,
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.1,
            "xanchor": "right",
            "x": 1,
        },
        xaxis_title=None,
        yaxis_title=None,
    )
    fig.update_yaxes(visible=False, range=[0.6, 1.55])
    fig.update_xaxes(showgrid=False, tickformat="%b %d")
    apply_dark_theme(fig)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_methodology() -> None:
    """Render the compact research-note methodology expander."""
    with st.expander("METHODOLOGY", expanded=False):
        st.markdown(
            """
            <div class="crc-method">
            <p>
            The monitor estimates cross-asset carry for FX, rates, credit, equity and
            commodities, then scales each signal by 30-business-day realized volatility.
            The ratio is an ex-ante Sharpe-style score, not a forecast of total return.
            </p>
            <p>
            The macro centroid is the daily cross-sectional median of carry and
            volatility. Those two median series are converted into time-series z-scores,
            which avoids the mechanical zero problem created by averaging
            cross-sectional z-scores.
            </p>
            <p>
            The classifier maps the carry and volatility z-scores into Risk-On,
            Mid-Cycle, Late-Cycle or Deleveraging. A five-day confirmation rule smooths
            transitions and reduces dashboard flicker. Individual carry/vol ratios are
            clipped at +/-20 to keep low-volatility proxies from dominating the view.
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Asset class": "FX carry",
                        "Carry definition": "Short-rate differential by currency pair",
                        "Known limitation": "Policy-rate proxy, not true FX-swap forward carry",
                    },
                    {
                        "Asset class": "Rates",
                        "Carry definition": "Long yield minus US 3M T-bill yield",
                        "Known limitation": "Yield-curve proxy; no duration, financing or roll-down",
                    },
                    {
                        "Asset class": "Credit",
                        "Carry definition": "ETF distribution yield minus IEF yield",
                        "Known limitation": "Yahoo ETF yield proxy, not true OAS spread carry",
                    },
                    {
                        "Asset class": "Equity",
                        "Carry definition": "Earnings yield minus US 3M risk-free rate",
                        "Known limitation": "Trailing P/E held constant historically",
                    },
                    {
                        "Asset class": "Commodity",
                        "Carry definition": "Roll/funding proxies from futures and rates",
                        "Known limitation": "Yahoo lacks full futures curves; proxies are approximate",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        st.latex(r"\sigma_{t}^{ann}=\sqrt{252}\cdot std\left(r_{t-29:t}\right)")
        st.latex(r"CarryVolRatio_{i,t}=\frac{Carry_{i,t}^{ann}}{\sigma_{i,t}^{ann}}")
        st.latex(r"z_t=\frac{x_t-\mu(x)}{\sigma(x)}")


def render_sidebar(cache: PriceCache, fetch_results: dict[str, Any], cfg: AppConfig) -> bool:
    """Render the full sidebar and return whether the user requested a force refresh."""
    latest = _latest_panel()
    total = len(cfg.universe)
    fetched = sum(
        1 for result in fetch_results.values() if not getattr(result, "df", pd.DataFrame()).empty
    )
    stale = sum(1 for result in fetch_results.values() if getattr(result, "stale", False))

    with st.sidebar:
        st.markdown('<div class="crc-sidebar-title">Status</div>', unsafe_allow_html=True)
        stale_class = "crc-neg" if stale else ""
        st.markdown(
            f"""
            <div class="crc-sidebar-row"><span>Tickers fetched</span><strong>{fetched}/{total}</strong></div>
            <div class="crc-sidebar-row"><span>Stale tickers</span><strong class="{stale_class}">{stale}</strong></div>
            <div class="crc-sidebar-row"><span>Cache size</span><strong>{_cache_size_mb(cache):.1f} MB</strong></div>
            <div class="crc-sidebar-row"><span>Last fetch</span><strong>{_latest_fetch_time(fetch_results)}</strong></div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="crc-sidebar-section"></div>', unsafe_allow_html=True)
        st.markdown('<div class="crc-sidebar-title">Controls</div>', unsafe_allow_html=True)
        force = st.button("FORCE REFRESH", width="stretch")
        auto_refresh = st.toggle(
            "Auto-refresh",
            value=st.session_state.get("crc_auto_refresh", True),
            key="crc_auto_refresh_toggle",
        )
        st.session_state["crc_auto_refresh"] = auto_refresh

        st.markdown('<div class="crc-sidebar-section"></div>', unsafe_allow_html=True)
        with st.expander("UNIVERSE", expanded=False):
            for asset_class in AssetClass:
                assets = [asset for asset in cfg.universe if asset.asset_class == asset_class]
                if not assets:
                    continue
                st.markdown(
                    f'<div class="crc-sidebar-title">{_asset_class_label(asset_class)}</div>',
                    unsafe_allow_html=True,
                )
                for asset in assets:
                    row = latest[latest["asset"].eq(asset.label)] if not latest.empty else pd.DataFrame()
                    if row.empty and asset.ticker.endswith("=X") and not latest.empty:
                        body = asset.ticker.replace("=X", "")
                        row = latest[latest["asset"].eq(f"{body[:3]}/{body[3:]}")]
                    values = "--"
                    if not row.empty:
                        item = row.iloc[0]
                        values = f'{float(item["carry"]):+.2%} / {float(item["vol"]):.1%}'
                    st.markdown(
                        f"""
                        <div class="crc-universe-row">
                            <span>{html.escape(asset.ticker)}</span>
                            <span>{html.escape(asset.label)}</span>
                            <span>{html.escape(values)}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        with st.expander("DEBUG", expanded=False):
            if st.button("View logs", width="stretch"):
                log_path = Path("logs/carry_compass.log")
                if log_path.exists():
                    lines = log_path.read_text(errors="replace").splitlines()[-50:]
                    st.code("\n".join(lines) or "No log lines found.")
                else:
                    st.code("logs/carry_compass.log not found.")
            if st.button("View cache stats", width="stretch"):
                st.dataframe(cache.stats(), width="stretch", hide_index=True)

    return force
