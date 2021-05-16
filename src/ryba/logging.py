import enum
import logging
import logging.config
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, getLogger

from . import config

__all__ = [
    'CRITICAL', 'ERROR', 'WARNING', 'MESSAGE', 'INFO', 'DEBUG', 'NOTSET', 'getLogger',
]

MESSAGE = INFO + 5


class Verbosity(config.Singleton, enum.IntEnum):
    silent = 0
    minimal = 1
    some = 2
    all = 3


def setup_logging(config: config.Config) -> None:
    verbosity = config.get(Verbosity)

    logging.addLevelName(MESSAGE, 'MESSAGE')

    log_level = [WARNING, MESSAGE, INFO, DEBUG][verbosity]
    logging.config.dictConfig({
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose" if verbosity >= Verbosity.all else "brief",
                "level": log_level,
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "ryba": {
                "handlers": ["console"],
                "level": logging.DEBUG,
            },
            "paramiko": {
                "handlers": ["console"],
                "level": logging.INFO if verbosity >= Verbosity.all else logging.WARNING,
            },
        },
        "formatters": {
            "verbose": {
                "class": "ryba.logging.ColouredLeaderFormatter",
                "format": "%(leader)s %(levelname)7s %(asctime)s %(name)s | %(message)s",
            },
            "brief": {
                "class": "ryba.logging.ColouredLeaderFormatter",
                "format": "%(leader)s %(message)s",
            },
        },
    })


def style(code: str, message: str) -> str:
    return f'\x1b[{code}m{message}\x1b[0m'


class ColouredLeaderFormatter(logging.Formatter):
    default_time_format = '%Y-%m-%d %H:%M:%S'
    default_msec_format = None  # type: ignore

    LEVEL_COLORS = {
        DEBUG: '1;37',
        INFO: '1;35',
        MESSAGE: '1;36',
        WARNING: '1;33',
        ERROR: '1;31',
        CRITICAL: '1;31;1',
    }

    def formatMessage(self, record: logging.LogRecord) -> str:
        leader = "==>"
        if record.levelno in self.LEVEL_COLORS:
            leader = style(self.LEVEL_COLORS[record.levelno], leader)
        record.leader = leader  # type: ignore
        return super().formatMessage(record)
