import logging
import logging.config
import typing as t
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING, getLogger

__all__ = [
    'CRITICAL', 'ERROR', 'WARNING', 'MESSAGE', 'INFO', 'DEBUG', 'NOTSET', 'getLogger',
]

MESSAGE = INFO + 5


def setup_logging(verbose_level: t.Union[t.Literal[0], t.Literal[1], t.Literal[2], t.Literal[3]]) -> None:
    logging.addLevelName(MESSAGE, 'MESSAGE')

    log_level = [WARNING, MESSAGE, INFO, DEBUG][verbose_level]
    logging.config.dictConfig({
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose" if verbose_level > 1 else "brief",
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
                "level": logging.INFO if verbose_level == 3 else logging.WARNING,
            },
        },
        "formatters": {
            "verbose": {
                "format": "[%(asctime)s %(levelname)s %(name)s]: %(message)s",
            },
            "brief": {
                "format": "%(message)s",
            },
        },
    })
