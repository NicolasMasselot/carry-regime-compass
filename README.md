# Carry Regime Compass

Cross-asset carry-to-volatility dashboard that turns market data into a quick macro regime read.

![Carry Regime Compass dashboard](docs/assets/carry-regime-compass-dashboard.png)

## Why

Carry only matters if the compensation is large enough relative to realized risk. This project packages that idea into an interactive dashboard for checking whether FX, rates, credit, equity, and commodity markets are rewarding carry or being dominated by volatility.

## What It Does

- Fetches market prices from Yahoo Finance and caches them locally in SQLite.
- Computes carry proxies by asset class, then normalizes them against 30-day realized volatility.
- Ranks assets by carry-to-volatility, similar to a simplified ex-ante Sharpe lens.
- Builds a cross-asset centroid and classifies the current market state as Risk-On, Mid-Cycle, Late-Cycle, or Deleveraging.
- Shows the current regime, recent transitions, asset ranking, scatter map, and methodology in Streamlit.

## Use It

```bash
git clone https://github.com/NicolasMasselot/carry-regime-compass.git
cd carry-regime-compass

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m streamlit run carry_compass/viz/app.py
```

Run the tests:

```bash
pytest
```

## Stack

- Python 3.11
- Streamlit and Plotly for the dashboard
- pandas, NumPy, SciPy, and yfinance for market data and analytics
- SQLAlchemy and SQLite for local price caching
- Pydantic and YAML for configuration
- pytest and Ruff for quality checks

## Project Structure

- `carry_compass/config/` defines the asset universe and regime thresholds.
- `carry_compass/data/` fetches and normalizes Yahoo Finance data.
- `carry_compass/cache/` stores price history locally.
- `carry_compass/carry/` computes asset-class-specific carry proxies.
- `carry_compass/vol/` computes realized volatility.
- `carry_compass/regime/` builds the centroid, classification, and transition smoothing.
- `carry_compass/viz/` contains the Streamlit app and Plotly components.
- `tests/` covers the core financial invariants and data-processing behavior.

## Known Limits

- FX carry is approximated with policy-rate differentials, not swap points.
- Credit uses ETF yield proxies rather than full OAS curves.
- Equity carry uses static earnings-yield inputs instead of point-in-time forecasts.
- Commodity carry is proxy-based because full futures curves are not available from Yahoo Finance.
