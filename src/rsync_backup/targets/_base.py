import abc
import datetime
import pathlib
import typing as t

import attr
import iso8601

from .. import config, constants, exceptions, registry


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class Backup:
    name: str = attr.ib(order=False)
    timestamp: datetime.datetime


class Target(config.Configurable, abc.ABC):
    name: str

    @classmethod
    def from_config_identifier(cls, identifier: str, config: config.Config) -> 'Target':
        """Create a new Target from a named target table in the config."""
        try:
            target_config = config["target"][identifier].copy()
        except KeyError:
            raise exceptions.ConfigError(f"Could not find 'targets.{identifier}' in config")

        try:
            target_type_name = target_config.pop("type")
        except KeyError:
            raise exceptions.ConfigError(f"Target 'targets.{identifier}' has no 'type'")

        try:
            target_type = target_types[target_type_name]
        except KeyError:
            raise exceptions.ConfigError(f"Unknown target type '{target_type_name}'")

        return target_type.from_options(identifier, target_config)

    @classmethod
    @abc.abstractmethod
    def from_options(cls, name: str, config: dict) -> "Target": ...

    @abc.abstractmethod
    def rsync_arguments(self, destination: pathlib.Path) -> t.Tuple[str, t.List[str]]: ...

    @abc.abstractmethod
    def connect(self) -> 'TargetContext':
        """
        Open a connection to the remote target, or mount the removable drive,
        or otherwise prepare the target for backing up to
        """
        ...


class TargetContext(t.ContextManager['TargetContext']):
    @abc.abstractmethod
    def make_path(self, path: pathlib.Path) -> pathlib.Path:
        """
        Take an absolute path and append it to the base path for this target.
        Useful for mounted media, for example.
        """

    @abc.abstractmethod
    def execute(self, cmd: t.List[str]) -> None:
        """Run a command on the target."""

    @abc.abstractmethod
    def exists(self, path: pathlib.Path) -> bool: ...

    @abc.abstractmethod
    def read_file(self, path: pathlib.Path) -> bytes: ...

    @abc.abstractmethod
    def write_file(self, path: pathlib.Path, contents: bytes) -> None: ...

    @abc.abstractmethod
    def list_directory(self, path: pathlib.Path) -> t.List[str]: ...

    def list_backups(self, path: pathlib.Path) -> t.Iterable[Backup]:
        """
        Find all the backups in a directory. A `(directory name, timestamp)`
        tuple is returned for each backup directory found.
        """
        entries = self.list_directory(path)
        for entry in entries:
            timestamp_file = path / entry / constants.TIMESTAMP_FILE_NAME
            if not self.exists(timestamp_file):
                continue
            content = self.read_file(timestamp_file).decode()
            try:
                yield Backup(name=entry, timestamp=iso8601.parse_date(content))
            except ValueError:
                continue


target_types = registry.Registry[t.Type[Target]]()
