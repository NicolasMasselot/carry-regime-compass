import datetime as dt
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from carry_compass.cache import PriceCache
from carry_compass.config import load_config
from carry_compass.data.batch import fetch_universe
from carry_compass.decision import (
    build_headline_call,
    maybe_notify,
    recent_transitions,
    record_new_transitions,
)
from carry_compass.regime.centroid import compute_centroid
from carry_compass.regime.classifier import regime_timeseries
from carry_compass.regime.transitions import detect_transitions, smoothed_regime
from carry_compass.utils.logging import configure_logging
from carry_compass.vol.panel import build_carry_vol_panel
from carry_compass.viz.components import (
    render_alert_banner,
    render_headline_call,
    render_how_to_read,
    render_kpi_strip,
    render_methodology,
    render_ranking_table,
    render_regime_timeline,
    render_scatter_dark,
    render_topbar,
)
from carry_compass.viz.pages.backtest import render_backtest_tab
from carry_compass.viz.styles import inject_global_css

st.set_page_config(
    page_title="Carry Regime Compass",
    layout="wide",
    page_icon="🧭",
    initial_sidebar_state="collapsed",
)


def _regime_label(value: object) -> str:
    return str(getattr(value, "value", value))


def _load_force_flag() -> bool:
    return bool(st.session_state.pop("crc_force_refresh_next", False))


def _last_transition_label(regimes: pd.DataFrame) -> str:
    transitions = detect_transitions(regimes)
    if not transitions:
        return "stable"

    last = transitions[-1]
    latest_date = pd.Timestamp(regimes.index.max()).date()
    days_ago = max((latest_date - last.confirmed_at).days, 0)
    return (
        f"{last.from_regime.value} → {last.to_regime.value} · "
        f"{days_ago} days ago"
    )


def _latest_cross_section(panel: pd.DataFrame) -> pd.DataFrame:
    """Return the most recent available observation for every asset."""
    return panel.sort_values(["asset", "date"]).groupby("asset", as_index=False).tail(1).copy()


def _latest_full_coverage_date(panel: pd.DataFrame) -> pd.Timestamp:
    """Return the latest date with all five asset classes represented."""
    class_counts = panel.groupby("date")["asset_class"].nunique()
    full_coverage = class_counts[class_counts >= 5]
    if full_coverage.empty:
        return pd.Timestamp(panel["date"].max())
    return pd.Timestamp(full_coverage.index.max())


def _latest_snapshot() -> Path | None:
    """Return the most recent prices parquet snapshot, or None if absent or stale."""
    snapshot_dir = Path("data/snapshots")
    if not snapshot_dir.exists():
        return None
    candidates = sorted(snapshot_dir.glob("prices_*.parquet"), reverse=True)
    if not candidates:
        return None
    latest = candidates[0]
    try:
        as_of = dt.date.fromisoformat(latest.stem.replace("prices_", ""))
    except ValueError:
        return None
    # Accept snapshots up to 3 calendar days old (covers weekends)
    if (dt.date.today() - as_of).days > 3:
        return None
    return latest


def _prices_from_snapshot(path: Path) -> dict[str, pd.DataFrame]:
    """Reconstruct a prices dict from a wide adj_close parquet snapshot."""
    wide = pd.read_parquet(path)
    prices: dict[str, pd.DataFrame] = {}
    for ticker in wide.columns:
        close = wide[ticker].dropna()
        if close.empty:
            continue
        prices[ticker] = pd.DataFrame(
            {
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "adj_close": close,
                "volume": 0.0,
            }
        )
    return prices


@st.cache_data(ttl=300, show_spinner="Loading data...")
def _load_panel(force: bool = False):
    fetch_results: dict = {}
    snapshot = None if force else _latest_snapshot()

    if snapshot is not None:
        prices = _prices_from_snapshot(snapshot)
        st.session_state["crc_data_source"] = f"snapshot:{snapshot.stem}"
    else:
        res = fetch_universe(force_refresh=force)
        prices = {ticker: result.df for ticker, result in res.items() if not result.df.empty}
        fetch_results = res
        st.session_state["crc_data_source"] = "live"

    panel = build_carry_vol_panel(prices)
    centroid = compute_centroid(panel)
    regimes = regime_timeseries(centroid)
    regimes["regime_smoothed"] = smoothed_regime(regimes)
    return panel, centroid, regimes, fetch_results, prices


def main() -> None:
    """Run the Streamlit dashboard."""
    configure_logging()
    inject_global_css()

    cfg = load_config()
    cache = PriceCache(cfg.cache.sqlite_path)

    auto_refresh = st.session_state.get("crc_auto_refresh", True)
    if auto_refresh:
        st_autorefresh(interval=cfg.refresh_seconds * 1000, key="auto_refresh_tick")

    force_refresh = _load_force_flag()
    panel, centroid, regimes, fetch_results, prices = _load_panel(force=force_refresh)
    now_utc = dt.datetime.now(dt.UTC)

    if panel.empty or regimes.empty:
        render_topbar(fetch_results, now_utc)
        st.error("No data available. Check logs/carry_compass.log.")
        return

    last_date = panel["date"].max()
    latest = _latest_cross_section(panel)
    latest_min_date = latest["date"].min()
    regime_date = _latest_full_coverage_date(panel)
    display_regimes = regimes.loc[:regime_date]
    st.session_state["crc_latest_panel"] = latest

    render_topbar(fetch_results, now_utc)

    col_cap, col_btn = st.columns([0.88, 0.12])
    with col_cap:
        st.markdown(
            f"""
            <div class="crc-page-caption">
                Cross-asset carry-to-volatility monitor · Yahoo Finance ·
                latest per-asset observations {latest_min_date.strftime("%Y-%m-%d")}
                to {last_date.strftime("%Y-%m-%d")} · regime date {regime_date.strftime("%Y-%m-%d")}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("Refresh data", use_container_width=True):
            _load_panel.clear()
            st.session_state["crc_force_refresh_next"] = True
            st.rerun()

    last_regime_row = display_regimes.iloc[-1]
    current_regime = _regime_label(
        last_regime_row.get("regime_smoothed") or last_regime_row["regime"]
    )

    # --- alert banner and transitions (shared across tabs) ---
    new_transitions = record_new_transitions(display_regimes, cache)
    secrets: dict = {}
    try:
        secrets = dict(st.secrets)
    except Exception:
        secrets = dict(os.environ)
    if new_transitions:
        maybe_notify(new_transitions, secrets)
    alerts = recent_transitions(display_regimes, lookback_days=7)
    if alerts:
        render_alert_banner(alerts)

    tab_dash, tab_bt = st.tabs(["DASHBOARD", "BACKTEST"])

    with tab_dash:
        # --- headline call ---
        call = build_headline_call(display_regimes, latest)
        render_headline_call(call)

        # --- KPI strip (supporting metrics) ---
        render_kpi_strip(
            current_regime,
            float(last_regime_row["carry_z"]),
            float(last_regime_row["vol_z"]),
            _last_transition_label(display_regimes),
        )

        render_how_to_read()

        # --- evidence: carry/vol map and asset ranking ---
        col_left, col_right = st.columns([0.6, 0.4], gap="medium")
        with col_left:
            st.markdown(
                '<div class="crc-section-title">Carry/Vol Map · Latest Per Asset</div>',
                unsafe_allow_html=True,
            )
            trail = centroid.tail(60)[["carry_med", "vol_med"]]
            render_scatter_dark(latest, trail)

        with col_right:
            st.markdown('<div class="crc-section-title">Asset Ranking</div>', unsafe_allow_html=True)
            render_ranking_table(latest)

        # --- history ---
        st.markdown('<div class="crc-section-title">Regime Timeline</div>', unsafe_allow_html=True)
        render_regime_timeline(display_regimes)
        render_methodology()

    with tab_bt:
        render_backtest_tab(panel, display_regimes, prices, cfg)


if __name__ == "__main__":
    main()
