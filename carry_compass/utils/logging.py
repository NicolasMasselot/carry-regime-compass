import sys
from pathlib import Path

from loguru import logger

_CONFIGURED = False


def configure_logging(level: str = "INFO", log_dir: Path = Path("logs")) -> None:
    """Configure loguru console and rotating file logging.

    Args:
        level: Minimum console log level.
        log_dir: Directory for ``carry_compass.log``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=level, enqueue=True)
    logger.add(
        log_dir / "carry_compass.log",
        level="DEBUG",
        rotation="10 MB",
        retention=5,
        enqueue=True,
    )
    _CONFIGURED = True
