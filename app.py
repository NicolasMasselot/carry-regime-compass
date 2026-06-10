from __future__ import annotations

import datetime as dt
import html
import time
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from carry_compass.config import load_config
from carry_compass.data.batch import fetch_universe
from carry_compass.regime.centroid import compute_centroid
from carry_compass.regime.classifier import regime_timeseries
from carry_compass.regime.transitions import detect_transitions, smoothed_regime
from carry_compass.vol.panel import build_carry_vol_panel
from carry_compass.viz.theme import ASSET_CLASS_COLORS_DARK, REGIME_COLORS_DARK, TEXT_SECONDARY

app = FastAPI(title="Carry Regime Compass")

_CACHE_TTL_SECONDS = 300
_snapshot_cache: dict[str, Any] = {"expires_at": 0.0, "html": ""}


def _configure_vercel_cache_path() -> None:
    cfg = load_config()
    if Path("/tmp").exists():
        cfg.cache.sqlite_path = Path("/tmp/carry-regime-compass/prices.db")


def _regime_label(value: object) -> str:
    return str(getattr(value, "value", value))


def _asset_label(value: object) -> str:
    return str(value).replace("_", " ").upper()


def _latest_cross_section(panel: pd.DataFrame) -> pd.DataFrame:
    return panel.sort_values(["asset", "date"]).groupby("asset", as_index=False).tail(1).copy()


def _latest_full_coverage_date(panel: pd.DataFrame) -> pd.Timestamp:
    class_counts = panel.groupby("date")["asset_class"].nunique()
    full_coverage = class_counts[class_counts >= 5]
    if full_coverage.empty:
        return pd.Timestamp(panel["date"].max())
    return pd.Timestamp(full_coverage.index.max())


def _last_transition_label(regimes: pd.DataFrame) -> str:
    transitions = detect_transitions(regimes)
    if not transitions:
        return "Stable"
    last = transitions[-1]
    latest_date = pd.Timestamp(regimes.index.max()).date()
    days_ago = max((latest_date - last.confirmed_at).days, 0)
    return f"{last.from_regime.value} to {last.to_regime.value}, {days_ago} days ago"


def _figure_html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})


def _scatter(latest: pd.DataFrame, centroid: pd.DataFrame) -> str:
    fig = px.scatter(
        latest,
        x="carry",
        y="vol",
        color="asset_class",
        color_discrete_map=ASSET_CLASS_COLORS_DARK,
        hover_name="asset",
        hover_data={"ratio": ":.2f", "carry": ":.2%", "vol": ":.2%"},
    )
    fig.update_traces(marker={"size": 13, "line": {"color": "#111111", "width": 1}})
    trail = centroid.tail(60)[["carry_med", "vol_med"]].reset_index().rename(columns={"index": "date"})
    if not trail.empty:
        fig.add_trace(
            go.Scatter(
                x=trail["carry_med"],
                y=trail["vol_med"],
                mode="lines+markers",
                name="Centroid trail",
                line={"color": "rgba(255,255,255,0.34)", "dash": "dot", "width": 1.5},
                marker={"size": 5, "color": "rgba(255,255,255,0.38)"},
                hovertemplate="Centroid<br>Carry=%{x:.2%}<br>Vol=%{y:.2%}<extra></extra>",
            )
        )
    fig.update_layout(
        template="plotly_dark",
        height=520,
        paper_bgcolor="#141414",
        plot_bgcolor="#0a0a0a",
        margin={"l": 20, "r": 20, "t": 8, "b": 20},
        legend={"title": "", "orientation": "h", "y": -0.18},
        xaxis_title="Carry annualized",
        yaxis_title="Realized volatility, 30D annualized",
        font={"family": "Inter, system-ui, sans-serif", "color": "#e8e8e8"},
    )
    fig.update_xaxes(tickformat=".0%", gridcolor="#1f1f1f", zerolinecolor="#2a2a2a")
    fig.update_yaxes(tickformat=".0%", gridcolor="#1f1f1f", zerolinecolor="#2a2a2a")
    return _figure_html(fig)


def _timeline(regimes: pd.DataFrame) -> str:
    frame = regimes.tail(180).copy()
    frame["regime_label"] = frame["regime_smoothed"].map(_regime_label)
    colors = [REGIME_COLORS_DARK.get(label, TEXT_SECONDARY) for label in frame["regime_label"]]
    fig = go.Figure(
        go.Bar(
            x=frame.index,
            y=[1] * len(frame),
            marker={"color": colors},
            customdata=frame[["regime_label", "carry_z", "vol_z"]],
            hovertemplate="%{x|%Y-%m-%d}<br>%{customdata[0]}<br>"
            "Carry z=%{customdata[1]:+.2f}<br>Vol z=%{customdata[2]:+.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=150,
        paper_bgcolor="#141414",
        plot_bgcolor="#141414",
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        showlegend=False,
        font={"family": "Inter, system-ui, sans-serif", "color": "#e8e8e8"},
    )
    fig.update_yaxes(visible=False)
    fig.update_xaxes(gridcolor="#1f1f1f")
    return _figure_html(fig)


def _ranking(latest: pd.DataFrame) -> str:
    rows = []
    ranked = latest.sort_values("ratio", ascending=False).head(12)
    for _, row in ranked.iterrows():
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['asset']))}</td>"
            f"<td>{html.escape(_asset_label(row['asset_class']))}</td>"
            f"<td>{row['carry']:.2%}</td>"
            f"<td>{row['vol']:.2%}</td>"
            f"<td>{row['ratio']:.2f}</td>"
            "</tr>"
        )
    return "".join(rows)


def _build_dashboard_html() -> str:
    _configure_vercel_cache_path()

    fetch_results = fetch_universe(max_workers=4)
    prices = {ticker: result.df for ticker, result in fetch_results.items() if not result.df.empty}
    panel = build_carry_vol_panel(prices)
    if panel.empty:
        raise RuntimeError("No market data available from Yahoo Finance or cache.")

    centroid = compute_centroid(panel)
    regimes = regime_timeseries(centroid)
    regimes["regime_smoothed"] = smoothed_regime(regimes)

    latest = _latest_cross_section(panel)
    regime_date = _latest_full_coverage_date(panel)
    display_regimes = regimes.loc[:regime_date]
    row = display_regimes.iloc[-1]
    current_regime = _regime_label(row.get("regime_smoothed") or row["regime"])
    color = REGIME_COLORS_DARK.get(current_regime, "#888888")
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    latest_min_date = latest["date"].min().strftime("%Y-%m-%d")
    latest_max_date = latest["date"].max().strftime("%Y-%m-%d")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Carry Regime Compass</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #0a0a0a; color: #e8e8e8; }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; padding: 22px 0 40px; }}
    header {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid #2a2a2a; padding-bottom: 16px; }}
    h1 {{ margin: 0; font-size: clamp(24px, 4vw, 38px); letter-spacing: 0; }}
    .sub {{ color: #a3a3a3; font-size: 14px; margin-top: 8px; }}
    .status {{ border: 1px solid #2a2a2a; background: #141414; padding: 10px 12px; min-width: 160px; text-align: right; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {color}; margin-right: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 18px 0; }}
    .panel {{ background: #141414; border: 1px solid #2a2a2a; border-radius: 8px; padding: 14px; }}
    .label {{ color: #888888; font-size: 12px; text-transform: uppercase; }}
    .value {{ font-size: 24px; margin-top: 8px; }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(300px, 0.85fr); gap: 14px; }}
    h2 {{ margin: 0 0 12px; font-size: 15px; color: #f5f5f5; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 9px 6px; border-bottom: 1px solid #242424; text-align: right; }}
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) {{ text-align: left; }}
    th {{ color: #888888; font-weight: 600; }}
    .method {{ color: #b5b5b5; line-height: 1.55; }}
    @media (max-width: 820px) {{ header, .layout {{ display: block; }} .status {{ margin-top: 12px; text-align: left; }} .grid {{ grid-template-columns: 1fr 1fr; }} .panel {{ margin-bottom: 12px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Carry Regime Compass</h1>
        <div class="sub">Cross-asset carry-to-volatility monitor. Latest observations {latest_min_date} to {latest_max_date}. Refreshed {now}.</div>
      </div>
      <div class="status"><span class="dot"></span>{html.escape(current_regime)}</div>
    </header>
    <section class="grid">
      <div class="panel"><div class="label">Regime</div><div class="value">{html.escape(current_regime)}</div></div>
      <div class="panel"><div class="label">Carry z-score</div><div class="value">{float(row["carry_z"]):+.2f}</div></div>
      <div class="panel"><div class="label">Vol z-score</div><div class="value">{float(row["vol_z"]):+.2f}</div></div>
      <div class="panel"><div class="label">Last transition</div><div class="value" style="font-size:18px">{html.escape(_last_transition_label(display_regimes))}</div></div>
    </section>
    <section class="layout">
      <div class="panel"><h2>Carry/Vol Map</h2>{_scatter(latest, centroid)}</div>
      <div class="panel"><h2>Asset Ranking</h2><table><thead><tr><th>Asset</th><th>Class</th><th>Carry</th><th>Vol</th><th>Ratio</th></tr></thead><tbody>{_ranking(latest)}</tbody></table></div>
    </section>
    <section class="panel" style="margin-top:14px"><h2>Regime Timeline</h2>{_timeline(display_regimes)}</section>
    <section class="panel method" style="margin-top:14px"><h2>Methodology</h2>Carry proxies and 30-day realized volatility are computed across FX, rates, credit, equity and commodities. The macro regime is inferred from cross-sectional median carry and volatility z-scores, then smoothed to avoid one-day flips.</section>
  </main>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    now = time.time()
    if _snapshot_cache["html"] and now < _snapshot_cache["expires_at"]:
        return str(_snapshot_cache["html"])
    try:
        dashboard = _build_dashboard_html()
    except Exception as exc:
        trace = traceback.format_exc()
        dashboard = f"""<!doctype html><html><head><title>Carry Regime Compass</title></head>
<body style="background:#0a0a0a;color:#e8e8e8;font-family:system-ui;padding:32px">
<h1>Carry Regime Compass</h1>
<p>The dashboard could not fetch enough market data right now.</p>
<pre>{html.escape(repr(exc))}</pre>
<pre>{html.escape(trace)}</pre>
</body></html>"""
    _snapshot_cache.update({"html": dashboard, "expires_at": now + _CACHE_TTL_SECONDS})
    return dashboard
