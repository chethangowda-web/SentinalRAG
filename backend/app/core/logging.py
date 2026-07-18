import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    format_string = (
        "[%(asctime)s] %(levelname)-8s %(name)-25s %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
