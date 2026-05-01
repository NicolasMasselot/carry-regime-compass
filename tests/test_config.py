from carry_compass.config import load_config


def test_default_config_loads_expected_universe() -> None:
    cfg = load_config()
    tickers = [asset.ticker for asset in cfg.universe]

    assert len(cfg.universe) == 26
    assert len(tickers) == len(set(tickers))
    assert cfg.vol.window_days == 30
