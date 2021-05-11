#!/usr/bin/env python3
"""
Backup local files to remotes using rsync.
"""
import argparse
import contextlib
import datetime
import pathlib
import sys
import typing as t

import iso8601

from . import backup, config, exceptions, logging

logger = logging.getLogger()


def main() -> None:
    with handle_errors():
        arguments = get_arguments()
        config = get_config(arguments)
        logging.setup_logging(min(arguments.verbosity, 3))
        command = get_command(arguments)
        command(config, arguments)


@contextlib.contextmanager
def handle_errors() -> t.Iterator[None]:
    try:
        yield
    except exceptions.CommandError as exc:
        sys.stderr.write(exc.message)
        sys.exit(exc.exit_code)
    except KeyboardInterrupt:
        sys.exit(1)


# Command line argument handling

def _get_argparse_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
    )
    parser.add_argument(
        "-c", "--config", dest="config",
        help="The config file to use.",
        type=pathlib.Path, default=config.get_default_config_path(),
    )
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument(
        "-v", "--verbose", dest="verbosity",
        help=(
            "Include more output when running. "
            "Use multiple times to make it even more verbose."
        ),
        action="count", default=1,
    )
    verbosity.add_argument(
        "-q", "--quiet", dest="verbosity",
        help="Turn off all output except errors",
        action="store_const", const=0,
    )
    parser.add_argument(
        "-n", "--dry-run", dest="dry_run",
        help=(
            "Do not actually transfer any files or create any snapshots, "
            "but still test the config and report what would happen."
        ),
        action="store_true", default=False,
    )
    parser.add_argument(
        "-d", "--directory", dest="directories", metavar="DIRECTORY",
        help=(
            "Back up a specific directory. Can be used multiple times to "
            "back up multiple directories. Directories must be defined in the "
            "config."
        ),
        type=pathlib.Path, action="append",
    )
    parser.add_argument(
        "-t", "--timestamp", dest="timestamp",
        help=(
            "Timestamp used for creating snapshot directories. ISO8601 format. "
            "Defaults to the current UTC time."
        ),
        type=_parse_datetime,
        default=datetime.datetime.now().replace(tzinfo=datetime.timezone.utc),
    )
    return parser


def _parse_datetime(value: str) -> datetime.datetime:
    return iso8601.parse_date(value)


def get_arguments() -> argparse.Namespace:
    parser = _get_argparse_parser()
    return parser.parse_args()


# Commands to run

class TCommand(t.Protocol):
    def __call__(self, config: config.Config, arguments: argparse.Namespace) -> None: ...


def get_command(arguments: argparse.Namespace) -> TCommand:
    return backup_directories


def backup_directories(config: config.Config, arguments: argparse.Namespace) -> None:
    directories = backup.Directory.all_from_config(config)

    if arguments.directories:
        desired_directories = [p.expanduser() for p in arguments.directories]
        missing_directories = [
            dd for dd in desired_directories
            if not any(dd == d.source_path for d in directories)
        ]
        if missing_directories:
            raise exceptions.CommandError(
                f"Unknown directory: {str(missing_directories[0])!r}"
            )
        directories = [d for d in directories if d.source_path in desired_directories]

    for directory in directories:
        backup.backup_directory(
            directory,
            dry_run=arguments.dry_run,
            verbose=arguments.verbosity > 1,
            timestamp=arguments.timestamp,
        )


# Config helpers

def get_config(arguments: argparse.Namespace) -> config.Config:
    config_file = arguments.config
    if not config_file.exists():
        if config_file == config.get_default_config_path():
            return config.Config.defaults()
        raise exceptions.CommandError(
            f"Config file `{config_file}' does not exist",
        )
    return config.Config.from_file(config_file)


# Run the dang thing

if __name__ == '__main__':
    main()
