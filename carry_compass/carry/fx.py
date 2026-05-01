import pandas as pd

SHORT_RATES_PROXY = {
    "USD": 0.0500,
    "EUR": 0.0250,
    "JPY": 0.0050,
    "CHF": 0.0100,
    "GBP": 0.0475,
    "AUD": 0.0410,
    "NZD": 0.0475,
    "CAD": 0.0450,
    "BRL": 0.1175,
    "MXN": 0.1025,
    "TRY": 0.4500,
    "ZAR": 0.0775,
}
EM_FUNDED = {"USDBRL=X", "USDMXN=X", "USDTRY=X", "USDZAR=X"}


def _decode_fx_ticker(ticker: str) -> tuple[str, str]:
    body = ticker.replace("=X", "")
    return body[:3], body[3:]


def compute_fx_carry(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute FX carry from short-rate differentials.

    Args:
        prices: Mapping of Yahoo FX tickers to canonical OHLCV frames.

    Returns:
        Wide date x pair frame of annualized decimal carry.

    Notes:
        This is not true FX-swap carry; it uses constant indicative policy-rate
        proxies. USD/EM pairs are flipped to long EM currency versus short USD.
    """
    out: dict[str, pd.Series] = {}
    for ticker, df in prices.items():
        if not ticker.endswith("=X") or len(ticker.replace("=X", "")) != 6 or df.empty:
            continue
        c1, c2 = _decode_fx_ticker(ticker)
        r1 = SHORT_RATES_PROXY.get(c1)
        r2 = SHORT_RATES_PROXY.get(c2)
        if r1 is None or r2 is None:
            continue
        carry = (r2 - r1) if ticker in EM_FUNDED else (r1 - r2)
        out[f"{c1}/{c2}"] = pd.Series(carry, index=df.index, dtype="float64")

    return pd.DataFrame(out).sort_index()
