from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from carry_compass.backtest.engine import BacktestResult, run_backtest
from carry_compass.backtest.metrics import compute_metrics, compute_regime_diagnostics
from carry_compass.config.schema import AppConfig
from carry_compass.viz.theme import (
    NEGATIVE,
    POSITIVE,
    REGIME_COLORS_DARK,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    apply_dark_theme,
)


def _fmt_pct(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "--"
    return f"{v * 100:.1f}%"


def _fmt_2f(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "--"
    return f"{v:.2f}"


def _equity_curve(result: BacktestResult) -> pd.DataFrame:
    """Cumulative return curves starting at 100."""
    portf = (1 + result.portfolio).cumprod() * 100
    bench = (1 + result.benchmark).cumprod() * 100
    return pd.DataFrame({"Strategy": portf, "Benchmark": bench})


def _render_methodology() -> None:
    with st.expander("METHODOLOGY - READ BEFORE INTERPRETING RESULTS", expanded=True):
        st.markdown(
            """
            <div class="crc-method">
            <p><strong>What the backtest shows.</strong>
            A simple regime-conditional allocation is simulated day-by-day over the
            available history. The benchmark is equal-weight buy-and-hold of the same
            asset universe. No leverage is used. All returns are before taxes and fees
            except for the explicit transaction-cost assumption.
            </p>
            <p><strong>Allocation rule.</strong>
            Risk-On: equal-weight the top-N assets by carry/vol ratio.
            Mid-Cycle and Late-Cycle: equal-weight all tradeable assets.
            Deleveraging: 100% cash.
            The rule is fixed and contains no free parameters that were fit to the data.
            </p>
            <p><strong>Lookahead prevention.</strong>
            The allocation on any day t uses: (1) the regime label confirmed at the close
            of day t-1, and (2) carry/vol rankings as of day t-1. No information from
            day t or later enters the decision. The z-score normalization used in regime
            detection is computed over the full available sample, which introduces mild
            in-sample calibration of the normalization window - this is acknowledged as a
            limitation.
            </p>
            <p><strong>Tradeable universe.</strong>
            FX carry pairs, equity indices, credit ETFs, and commodity futures.
            Rate yield tickers (^IRX, ^FVX, ^TNX, ^TYX) are excluded because they are
            interest-rate levels, not directly investable price series. EM FX returns are
            sign-flipped so positive return = profit from long-EM carry trade.
            </p>
            <p><strong>History and split.</strong>
            With the default 400-day price history, the backtest covers roughly
            13 months. This is a short window: treat results as illustrative, not
            conclusive. To extend the history, increase <code>history_days</code> in
            <code>universe.yaml</code> and force-refresh the data.
            The in-sample window is shown for context only; no thresholds were fit to it.
            </p>
            <p><strong>Intellectual honesty.</strong>
            Results are shown as-is including periods of underperformance. A regime
            signal that looks good over 13 months is not robust evidence; it needs
            years of out-of-sample data to be taken seriously.
            </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_equity_chart(
    result: BacktestResult,
    regimes: pd.DataFrame,
) -> None:
    curves = _equity_curve(result)
    if curves.empty:
        st.caption("No equity curve available.")
        return

    regime_col = "regime_smoothed" if "regime_smoothed" in regimes.columns else "regime"

    fig = go.Figure()

    # Regime background bands
    dates = list(curves.index)
    reg_series = (
        regimes[regime_col]
        .reindex(dates)
        .ffill()
        .map(lambda v: str(getattr(v, "value", v)))
    )
    if not reg_series.empty:
        start_idx = 0
        labels = list(reg_series)
        for i in range(1, len(labels) + 1):
            if i < len(labels) and labels[i] == labels[start_idx]:
                continue
            label = labels[start_idx]
            x0 = dates[start_idx]
            x1 = dates[i - 1] if i < len(labels) else dates[-1]
            color = REGIME_COLORS_DARK.get(label, TEXT_SECONDARY)
            fig.add_vrect(
                x0=x0, x1=x1,
                fillcolor=color,
                opacity=0.07,
                layer="below",
                line_width=0,
            )
            start_idx = i

    # In-sample shading
    is_start = curves.index[0]
    oos = result.oos_start
    if oos > is_start:
        fig.add_vrect(
            x0=is_start, x1=oos,
            fillcolor="rgba(255,255,255,0.04)",
            layer="below",
            line={"color": "rgba(255,255,255,0.15)", "width": 1, "dash": "dot"},
            annotation_text="In-sample",
            annotation_position="top left",
            annotation_font={"size": 10, "color": TEXT_SECONDARY},
        )
        fig.add_vline(
            x=oos,
            line={"color": "rgba(255,255,255,0.45)", "width": 1, "dash": "dash"},
            annotation_text="OOS start",
            annotation_position="top right",
            annotation_font={"size": 10, "color": TEXT_SECONDARY},
        )

    oos_curves = curves[curves.index >= oos]

    # Benchmark line
    fig.add_trace(go.Scatter(
        x=curves.index,
        y=curves["Benchmark"],
        mode="lines",
        name="Benchmark (equal-weight)",
        line={"color": TEXT_SECONDARY, "width": 1.5, "dash": "dot"},
        hovertemplate="%{x|%Y-%m-%d}<br>Benchmark: %{y:.1f}<extra></extra>",
    ))

    # Portfolio line
    portf_color = POSITIVE if oos_curves.empty or oos_curves["Strategy"].iloc[-1] >= oos_curves["Benchmark"].iloc[-1] else NEGATIVE
    fig.add_trace(go.Scatter(
        x=curves.index,
        y=curves["Strategy"],
        mode="lines",
        name="Strategy",
        line={"color": portf_color, "width": 2},
        hovertemplate="%{x|%Y-%m-%d}<br>Strategy: %{y:.1f}<extra></extra>",
    ))

    fig.update_layout(
        height=380,
        yaxis_title="Cumulative return (start = 100)",
        xaxis_title=None,
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom", "y": 1.02,
            "xanchor": "right", "x": 1,
        },
    )
    fig.update_yaxes(tickprefix="", ticksuffix="")
    fig.update_xaxes(tickformat="%b %Y")
    apply_dark_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_metrics_table(result: BacktestResult) -> None:
    oos = result.oos_start

    def _table(portf: pd.Series, bench: pd.Series, label: str) -> None:
        if portf.empty:
            return
        m = compute_metrics(portf, bench)
        p = m.get("portfolio", {})
        b = m.get("benchmark", {})

        st.markdown(
            f'<div class="crc-label" style="margin-bottom:8px;">{html.escape(label)}</div>',
            unsafe_allow_html=True,
        )

        rows = [
            ("Ann. Return", _fmt_pct(p.get("Ann. Return")), _fmt_pct(b.get("Ann. Return"))),
            ("Ann. Volatility", _fmt_pct(p.get("Ann. Volatility")), _fmt_pct(b.get("Ann. Volatility"))),
            ("Sharpe Ratio", _fmt_2f(p.get("Sharpe Ratio")), _fmt_2f(b.get("Sharpe Ratio"))),
            ("Max Drawdown", _fmt_pct(p.get("Max Drawdown")), _fmt_pct(b.get("Max Drawdown"))),
            ("Hit Rate", _fmt_pct(p.get("Hit Rate")), _fmt_pct(b.get("Hit Rate"))),
            ("Ann. Excess Return", _fmt_pct(p.get("Ann. Excess Return")), "--"),
            ("Information Ratio", _fmt_2f(p.get("Information Ratio")), "--"),
        ]
        trs = "".join(
            f"<tr><td>{html.escape(r)}</td>"
            f'<td class="crc-num">{html.escape(pv)}</td>'
            f'<td class="crc-num">{html.escape(bv)}</td></tr>'
            for r, pv, bv in rows
        )
        st.markdown(
            f'<table class="crc-table" style="width:100%;margin-bottom:16px;">'
            f"<thead><tr><th>Metric</th><th class='crc-num'>Strategy</th>"
            f"<th class='crc-num'>Benchmark</th></tr></thead>"
            f"<tbody>{trs}</tbody></table>",
            unsafe_allow_html=True,
        )

    col_oos, col_full = st.columns(2, gap="medium")
    with col_oos:
        oos_p = result.portfolio[result.portfolio.index >= oos]
        oos_b = result.benchmark[result.benchmark.index >= oos]
        _table(oos_p, oos_b, f"Out-of-sample ({oos.strftime('%Y-%m-%d')} onwards)")
    with col_full:
        _table(result.portfolio, result.benchmark, "Full period")


def _render_diagnostics(result: BacktestResult) -> None:
    oos_p = result.portfolio[result.portfolio.index >= result.oos_start]
    oos_r = result.regimes_used[result.regimes_used.index >= result.oos_start]
    diag = compute_regime_diagnostics(oos_p, oos_r)

    if diag.empty:
        st.caption("No regime diagnostic data available.")
        return

    st.markdown(
        '<div class="crc-label" style="margin-bottom:8px;">'
        "Return by regime (out-of-sample): how often each regime was followed by above-median returns"
        "</div>",
        unsafe_allow_html=True,
    )

    rows_html = []
    for _, row in diag.iterrows():
        regime = str(row["Regime"])
        color = REGIME_COLORS_DARK.get(regime, TEXT_SECONDARY)
        above = float(row["Above Median"])
        above_color = POSITIVE if above >= 0.5 else NEGATIVE
        rows_html.append(
            f"<tr>"
            f"<td><span class='crc-dot crc-mini-dot' style='background:{color};'></span>"
            f" {html.escape(regime)}</td>"
            f'<td class="crc-num">{int(row["Days"])}</td>'
            f'<td class="crc-num">{_fmt_pct(row["Ann. Return"])}</td>'
            f'<td class="crc-num">{_fmt_pct(row["Hit Rate"])}</td>'
            f'<td class="crc-num" style="color:{above_color};">{_fmt_pct(above)}</td>'
            f"</tr>"
        )
    st.markdown(
        '<table class="crc-table" style="width:100%;">'
        "<thead><tr>"
        "<th>Regime</th><th class='crc-num'>Days</th>"
        "<th class='crc-num'>Ann. Return</th><th class='crc-num'>Hit Rate</th>"
        "<th class='crc-num'>Above Median</th>"
        "</tr></thead>"
        f'<tbody>{"".join(rows_html)}</tbody>'
        "</table>",
        unsafe_allow_html=True,
    )


def _render_validation_chart(
    regimes: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
) -> None:
    """Regime-colored background over the S&P 500 price series."""
    gspc = prices.get("^GSPC")
    if gspc is None or gspc.empty:
        st.caption("S&P 500 price data not available for validation chart.")
        return

    col = "adj_close" if "adj_close" in gspc.columns and gspc["adj_close"].notna().any() else "close"
    price = gspc[col].dropna()
    if price.empty:
        return

    regime_col = "regime_smoothed" if "regime_smoothed" in regimes.columns else "regime"
    reg_dates = sorted(set(price.index) & set(regimes.index))
    if not reg_dates:
        st.caption("No overlapping dates between price data and regime series.")
        return

    fig = go.Figure()

    # Regime background bands
    reg_series = (
        regimes[regime_col]
        .reindex(reg_dates)
        .ffill()
        .map(lambda v: str(getattr(v, "value", v)))
    )
    labels = list(reg_series)
    dates_v = list(reg_series.index)
    start_idx = 0
    for i in range(1, len(labels) + 1):
        if i < len(labels) and labels[i] == labels[start_idx]:
            continue
        label = labels[start_idx]
        x0 = dates_v[start_idx]
        x1 = dates_v[i - 1] if i < len(labels) else dates_v[-1]
        color = REGIME_COLORS_DARK.get(label, TEXT_SECONDARY)
        fig.add_vrect(
            x0=x0, x1=x1,
            fillcolor=color,
            opacity=0.12,
            layer="below",
            line_width=0,
            annotation_text=label if i == start_idx + 1 else "",
        )
        start_idx = i

    # Price line
    fig.add_trace(go.Scatter(
        x=price.index,
        y=price.values,
        mode="lines",
        name="S&P 500",
        line={"color": TEXT_PRIMARY, "width": 1.5},
        hovertemplate="%{x|%Y-%m-%d}<br>S&P 500: %{y:,.0f}<extra></extra>",
    ))

    start_str = pd.Timestamp(price.index.min()).strftime("%Y-%m-%d")
    end_str = pd.Timestamp(price.index.max()).strftime("%Y-%m-%d")

    fig.update_layout(
        height=260,
        title={
            "text": f"S&P 500 with regime overlays ({start_str} to {end_str})",
            "font": {"size": 12, "color": TEXT_SECONDARY},
            "x": 0,
            "pad": {"l": 0},
        },
        xaxis_title=None,
        yaxis_title="Price (USD)",
        showlegend=False,
        hovermode="x unified",
        margin={"t": 36},
    )
    fig.update_xaxes(tickformat="%b %Y")
    apply_dark_theme(fig)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    note = (
        "Note: the available price history starts "
        + start_str
        + ". To validate against the March 2020 crash or the 2022 drawdown, "
        "increase <code>history_days</code> in <code>universe.yaml</code> "
        "to 2000 and force-refresh the data."
    )
    st.markdown(
        f'<div class="crc-subvalue" style="margin-top:4px;">{note}</div>',
        unsafe_allow_html=True,
    )


def render_backtest_tab(
    panel: pd.DataFrame,
    regimes: pd.DataFrame,
    prices: dict[str, pd.DataFrame],
    cfg: AppConfig,
) -> None:
    """Render the full backtest tab content.

    Args:
        panel: Long-format carry/vol panel from _load_panel.
        regimes: Date-indexed regime DataFrame with regime_smoothed column.
        prices: Dict of {ticker: OHLCV DataFrame} for all universe tickers.
        cfg: Loaded AppConfig.
    """
    if panel.empty or regimes.empty:
        st.warning("No data available for backtest. Check the data pipeline.")
        return

    _render_methodology()

    st.markdown('<div class="crc-section-title">Parameters</div>', unsafe_allow_html=True)
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1], gap="medium")

    valid_dates = sorted(regimes.index)
    min_date = pd.Timestamp(valid_dates[0]).date()
    max_date = pd.Timestamp(valid_dates[-1]).date()
    default_oos = pd.Timestamp(valid_dates[len(valid_dates) // 2]).date()

    with ctrl_col1:
        oos_input = st.date_input(
            "Out-of-sample start date",
            value=default_oos,
            min_value=min_date,
            max_value=max_date,
            help="Data before this date is in-sample (for context only). "
                 "Metrics are reported on the out-of-sample window.",
            key="bt_oos_start",
        )
    with ctrl_col2:
        tc_bps = st.slider(
            "Transaction cost (bps per trade)",
            min_value=0,
            max_value=20,
            value=5,
            step=1,
            help="One-way cost in basis points applied to daily turnover.",
            key="bt_tc_bps",
        )
    with ctrl_col3:
        top_n = st.slider(
            "Top-N assets in Risk-On",
            min_value=3,
            max_value=min(10, len(panel["asset"].unique()) if not panel.empty else 10),
            value=5,
            step=1,
            help="Number of highest-carry assets to hold when regime is Risk-On.",
            key="bt_top_n",
        )

    oos_start = pd.Timestamp(oos_input)

    with st.spinner("Running backtest..."):
        result = run_backtest(
            regimes=regimes,
            panel=panel,
            prices=prices,
            cfg=cfg,
            oos_start=oos_start,
            tc_bps=float(tc_bps),
            top_n_risk_on=top_n,
        )

    if result.portfolio.empty:
        st.warning("Backtest returned no results. The dataset may be too short.")
        return

    st.markdown('<div class="crc-section-title">Equity Curve</div>', unsafe_allow_html=True)
    _render_equity_chart(result, regimes)

    st.markdown('<div class="crc-section-title">Performance Metrics</div>', unsafe_allow_html=True)
    _render_metrics_table(result)

    st.markdown('<div class="crc-section-title">Return by Regime (Out-of-Sample)</div>', unsafe_allow_html=True)
    _render_diagnostics(result)

    st.markdown('<div class="crc-section-title">Regime Validation: S&P 500</div>', unsafe_allow_html=True)
    _render_validation_chart(regimes, prices)
