import argparse

from carry_compass.cache.dao import PriceCache
from carry_compass.config import load_config
from carry_compass.utils.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    """Build the cache maintenance CLI parser.

    Returns:
        Parser with init, stats and purge subcommands.
    """
    parser = argparse.ArgumentParser(prog="python -m carry_compass.cache.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="Create the SQLite cache schema.")
    subparsers.add_parser("stats", help="Show per-ticker cache stats.")
    purge = subparsers.add_parser("purge", help="Delete cached prices.")
    purge.add_argument("--ticker", help="Only purge one ticker.")
    return parser


def main() -> None:
    """Run cache maintenance commands from the command line."""
    args = build_parser().parse_args()
    configure_logging()
    cfg = load_config()
    cache = PriceCache(cfg.cache.sqlite_path)

    if args.command == "init":
        print(f"initialized {cfg.cache.sqlite_path}")
    elif args.command == "stats":
        stats = cache.stats()
        print("no cached prices" if stats.empty else stats.to_string(index=False))
    elif args.command == "purge":
        deleted = cache.purge(args.ticker)
        print(f"deleted {deleted} rows")


if __name__ == "__main__":
    main()
