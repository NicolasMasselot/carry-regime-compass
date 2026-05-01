import argparse

from carry_compass.data.batch import fetch_universe
from carry_compass.data.fetcher import DataFetcher
from carry_compass.utils.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the data-fetch CLI parser.

    Returns:
        Parser with single-ticker and full-universe fetch commands.
    """
    parser = argparse.ArgumentParser(prog="python -m carry_compass.data.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch one ticker history.")
    fetch.add_argument("ticker")
    fetch.add_argument("--force", action="store_true", help="Force a network refresh.")

    subparsers.add_parser("fetch-all", help="Fetch all configured tickers.")
    return parser


def main() -> None:
    """Run data-fetch commands from the command line."""
    args = build_parser().parse_args()
    configure_logging()

    if args.command == "fetch":
        result = DataFetcher().fetch_history(args.ticker, force_refresh=args.force)
        print(
            f"{result.ticker}: source={result.source}, rows_added={result.rows_added}, "
            f"total={len(result.df)}, stale={result.stale}"
        )
        print(result.df.tail())
    elif args.command == "fetch-all":
        results = fetch_universe()
        for ticker in sorted(results):
            result = results[ticker]
            print(
                f"{ticker:<14} src={result.source:<8} +{result.rows_added:>3} rows "
                f"total={len(result.df):>4} stale={result.stale}"
            )


if __name__ == "__main__":
    main()
