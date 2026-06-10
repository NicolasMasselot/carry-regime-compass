from __future__ import annotations

import logging
from datetime import timedelta

import pandas as pd

from carry_compass.cache.dao import PriceCache
from carry_compass.regime.transitions import Transition, detect_transitions

logger = logging.getLogger(__name__)


def record_new_transitions(
    regimes: pd.DataFrame,
    cache: PriceCache,
) -> list[Transition]:
    """Persist any new regime transitions and return those not yet recorded.

    Args:
        regimes: Date-indexed frame with a ``regime`` column.
        cache: PriceCache instance used to read and write the regime_log table.

    Returns:
        List of transitions newly inserted into the log.
    """
    transitions = detect_transitions(regimes)
    if not transitions:
        return []

    known = cache.known_transition_dates()
    new = [t for t in transitions if t.confirmed_at not in known]
    for t in new:
        cache.upsert_transition(
            from_regime=t.from_regime.value,
            to_regime=t.to_regime.value,
            confirmed_at=t.confirmed_at,
        )
    if new:
        logger.info("Recorded %d new regime transition(s).", len(new))
    return new


def recent_transitions(
    regimes: pd.DataFrame,
    lookback_days: int = 7,
) -> list[Transition]:
    """Return transitions confirmed within lookback_days of the latest regime date.

    Args:
        regimes: Date-indexed regime frame.
        lookback_days: How many calendar days back to consider recent.

    Returns:
        Filtered list of Transition objects, most recent last.
    """
    transitions = detect_transitions(regimes)
    if not transitions or regimes.empty:
        return []
    latest_date = pd.Timestamp(regimes.index.max()).date()
    cutoff = latest_date - timedelta(days=lookback_days)
    return [t for t in transitions if t.confirmed_at >= cutoff]


def _send_webhook(transition: Transition, endpoint: str) -> None:
    """POST a regime transition payload to a webhook endpoint.

    Not called unless WEBHOOK_URL is present in secrets. Failures are logged
    as warnings and never raised to the caller.
    """
    import json
    import urllib.request

    payload = json.dumps(
        {
            "from": transition.from_regime.value,
            "to": transition.to_regime.value,
            "date": str(transition.confirmed_at),
        }
    ).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
        logger.info("Transition webhook sent: %s -> %s", transition.from_regime.value, transition.to_regime.value)
    except Exception as exc:
        logger.warning("Webhook notification failed: %s", exc)


def maybe_notify(transitions: list[Transition], secrets: dict) -> None:
    """Fire a webhook for new transitions if WEBHOOK_URL is configured.

    Off by default. Set ``WEBHOOK_URL`` in Streamlit secrets (secrets.toml)
    or as an environment variable to enable.

    Args:
        transitions: Newly recorded transitions from record_new_transitions().
        secrets: Dict-like of Streamlit secrets or os.environ.
    """
    endpoint = secrets.get("WEBHOOK_URL", "")
    if not endpoint:
        return
    for transition in transitions:
        _send_webhook(transition, endpoint)
