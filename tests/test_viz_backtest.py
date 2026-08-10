import pandas as pd

from carry_compass.backtest.engine import BacktestResult
from carry_compass.viz.pages import backtest


def test_equity_chart_keeps_datetime_oos_line_and_annotation_separate(mocker) -> None:
    dates = pd.bdate_range("2025-01-01", periods=6)
    result = BacktestResult(
        portfolio=pd.Series(0.001, index=dates, name="portfolio"),
        benchmark=pd.Series(0.0005, index=dates, name="benchmark"),
        weights=pd.DataFrame(index=dates),
        regimes_used=pd.Series("Risk-On", index=dates, name="regime_used"),
        oos_start=dates[3],
    )
    regimes = pd.DataFrame({"regime": "Risk-On"}, index=dates)
    plotly_chart = mocker.patch.object(backtest.st, "plotly_chart")

    backtest._render_equity_chart(result, regimes)

    figure = plotly_chart.call_args.args[0]
    oos_lines = [
        shape
        for shape in figure.layout.shapes
        if shape.type == "line" and shape.line.dash == "dash"
    ]
    oos_annotations = [
        annotation
        for annotation in figure.layout.annotations
        if annotation.text == "OOS start"
    ]

    assert len(oos_lines) == 1
    assert oos_lines[0].x0 == result.oos_start
    assert oos_lines[0].x1 == result.oos_start
    assert len(oos_annotations) == 1
    assert oos_annotations[0].x == result.oos_start
    assert oos_annotations[0].xref == "x"
    assert oos_annotations[0].y == 1
    assert oos_annotations[0].yref == "paper"
    assert oos_annotations[0].xanchor == "left"
    assert oos_annotations[0].yanchor == "top"
