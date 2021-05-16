import datetime
import pathlib
import typing as t

import attr

from . import config, constants, exceptions, rotators, targets


@attr.s(auto_attribs=True, kw_only=True, )
class Directory:
    source_path: pathlib.Path
    target_path: pathlib.Path
    target: targets.Target
    rotate: t.Optional[rotators.Rotator] = None

    exclude_from: t.Optional[pathlib.Path] = None
    exclude_files: t.List[str] = attr.ib(factory=list)

    one_file_system: bool = True

    @classmethod
    def all_from_config(cls, config: config.Config) -> t.List['Directory']:
        """
        Create a Directory for every directory found in the config.
        """
        return [cls.from_options(entry, config) for entry in config["backup"]]

    @classmethod
    def from_options(cls, directory: dict, config: config.Config) -> 'Directory':
        """
        Create a Directory from a config stored in a dictionary.
        This can be used to create Directories from configuration loaded from a file,
        for example.
        """
        directory = directory.copy()
        target_bits = directory.pop('target').split(':', 2)

        source_path = pathlib.Path(directory.pop("source")).expanduser()
        target_path = pathlib.Path(target_bits[1]).expanduser()

        target = config.get((targets.Target, target_bits[0]))  # type: ignore
        if (rotator_name := directory.pop('rotate', None)) is not None:
            rotate = config.get((rotators.Rotator, rotator_name))  # type: ignore
        else:
            rotate = None

        exclude_from = None
        if 'exclude_from' in directory:
            exclude_from = pathlib.Path(directory.pop('exclude_from')).expanduser()

        return cls(
            source_path=source_path, target_path=target_path,
            target=target, rotate=rotate,
            exclude_from=exclude_from, **directory)

    def resolve_exclude_from(self) -> t.Optional[pathlib.Path]:
        """
        Resolve the absolute path to the `exclude_file`, if one is defind.
        If `exclude_file` is set and absolute, that path is used.
        If `exclude_file` is set and relative, it is combined with `source_path` to
        make an absolute path.
        If `exclude_file` is not set, but a `.rsync-exclude` file exists in `source_path`,
        the absolute path to that file is returned.
        If `exclude_file` is not set, `None` is returned.
        """
        if self.exclude_from is not None:
            exclude_from = self.exclude_from.expanduser()
            if not exclude_from.is_absolute():
                exclude_from = self.source_path / exclude_from
            if not exclude_from.exists():
                raise exceptions.ConfigError(f"{str(exclude_from)!r} does not exist")

            return exclude_from

        else:
            exclude_from = self.source_path.expanduser() / constants.EXCLUDE_FROM_FILE_NAME
            if exclude_from.exists():
                return exclude_from
            else:
                return None

    def snapshot_name(self, timestamp: datetime.datetime) -> str:
        """
        Convert a timestamp into a snapshot directory name.
        This should include the timestamp to make it unique,
        but the timestamp is never parsed from this filename.
        """
        return timestamp.strftime("snapshot-%Y-%m-%dT%H:%M:%S")

    def __str__(self) -> str:
        return f"{str(self.source_path)!r} to {self.target.name}:{str(self.target_path)!r}"
