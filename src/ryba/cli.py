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

from . import config, directories, exceptions, logging, rotators, targets
from .commands import backup, rotate

logger = logging.getLogger(__name__)


def main() -> None:
    with handle_errors():
        arguments = get_arguments()
        config = get_config(arguments)

        if arguments.verbosity is not None:
            verbosity = logging.Verbosity(min(arguments.verbosity + 1, 3))
        else:
            verbosity = logging.Verbosity(config['ryba']['verbosity'])
        config.set(logging.Verbosity, verbosity)

        logging.setup_logging(config)
        arguments.func(config, arguments)


@contextlib.contextmanager
def handle_errors() -> t.Iterator[None]:
    try:
        yield
    except exceptions.CommandError as exc:
        logger.error(exc.message)
        sys.exit(exc.exit_code)
    except KeyboardInterrupt:
        sys.exit(1)


# Command line argument handling

def _get_argparse_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "ryba",
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
        action="count",
    )
    verbosity.add_argument(
        "-q", "--quiet", dest="verbosity",
        help="Turn off all output except errors",
        action="store_const", const=0,
    )
    parser.set_defaults(verbosity=None)
    parser.set_defaults(func=cmd_default)

    subparsers = parser.add_subparsers(title="Commands")
    backup = subparsers.add_parser(
        "backup",
        description="Backup the configured directories")
    backup.add_argument(
        "-n", "--dry-run", dest="dry_run",
        help=(
            "Do not actually transfer any files or create any snapshots, "
            "but still test the config and report what would happen."
        ),
        action="store_true", default=False,
    )
    backup.add_argument(
        "-d", "--directory", dest="directories", metavar="DIRECTORY",
        help=(
            "Back up a specific directory. Can be used multiple times to "
            "back up multiple directories. Directories must be defined in the "
            "config."
        ),
        type=pathlib.Path, action="append",
    )
    backup.add_argument(
        "-t", "--timestamp", dest="timestamp",
        help=(
            "Timestamp used for creating snapshot directories. ISO8601 format. "
            "Defaults to the current UTC time."
        ),
        type=_parse_datetime,
        default=_utc_now(),
    )
    backup.set_defaults(func=cmd_backup)

    test_rotator = subparsers.add_parser(
        "test-rotator",
        description="Test a rotation strategy without making any changes")
    test_rotator.set_defaults(func=cmd_test_rotator)
    test_rotator.add_argument(
        "rotator",
        help="The name of a configured rotator to test")
    dates_source = test_rotator.add_mutually_exclusive_group(required=True)
    dates_source.add_argument(
        "--dates-from",
        help=(
            "The path to a file that contains one ISO8601 date time per line. "
            "These dates are taken as the timestamps of some backups to rotate."
        ),
        type=pathlib.Path)
    dates_source.add_argument(
        "--directory",
        help=(
            "The path of a configured backup directory. "
            "All backups found for this directory are used as the example backups to rotate. "
            "No actual changes will be made, and no backups will be removed."
        ),
        type=pathlib.Path)
    return parser


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)


def _parse_datetime(value: str) -> datetime.datetime:
    return iso8601.parse_date(value)


def get_arguments() -> argparse.Namespace:
    parser = _get_argparse_parser()
    return parser.parse_args()


# Commands to run

def _get_matching_directories(
    directories: t.List[directories.Directory], paths: t.Iterable[pathlib.Path]
) -> t.List[directories.Directory]:
    paths = set(paths)
    missing_directories = [
        p for p in paths
        if not any(p == d.source_path for d in directories)
    ]
    if missing_directories:
        raise exceptions.CommandError(
            f"Unknown directory: {str(missing_directories[0])!r}"
        )
    return [d for d in directories if d.source_path in paths]


def cmd_default(config: config.Config, arguments: argparse.Namespace) -> None:
    timestamp = _utc_now()
    for directory in directories.Directory.all_from_config(config):
        backup.backup_directory(directory, config=config, timestamp=timestamp)


def cmd_backup(config: config.Config, arguments: argparse.Namespace) -> None:
    directories_to_backup = directories.Directory.all_from_config(config)

    if arguments.directories:
        directories_to_backup = _get_matching_directories(
            directories_to_backup, [p.expanduser() for p in arguments.directories])

    for directory in directories_to_backup:
        backup.backup_directory(
            directory, config=config,
            dry_run=arguments.dry_run,
            timestamp=arguments.timestamp,
        )


def cmd_test_rotator(config: config.Config, arguments: argparse.Namespace) -> None:
    timestamp = _utc_now()
    rotator = config.get((rotators.Rotator, arguments.rotator))  # type: ignore
    logger.log(logging.MESSAGE, f"Using rotator {rotator}, type {type(rotator).__name__}")

    if arguments.directory:
        directory = next(iter(_get_matching_directories(
            directories.Directory.all_from_config(config),
            [arguments.directory.expanduser()])))
        with directory.target.connect() as context:
            backups = context.list_backups(directory.target_path)
    else:
        with open(arguments.dates_from, 'r') as f:
            trimmed_lines = (line.strip() for line in f)
            backups = [
                targets.Backup(name=line, timestamp=iso8601.parse_date(line))
                for line in trimmed_lines
            ]

    if (reason := rotator.should_rotate()) is not True:
        logger.log(logging.MESSAGE, f"Not rotating backups: {reason}")

    verdicts = sorted(rotator.rotate_backups(timestamp, list(backups)))
    for message in map(rotate.format_verdict_tuple, verdicts):
        logger.log(logging.MESSAGE, message)


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
