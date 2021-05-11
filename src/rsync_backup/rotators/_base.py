import abc
import datetime
import enum
import typing as t

from rsync_backup import config, registry

Verdict = enum.Enum("Verdict", ["keep", "drop"])


class Rotator(config.Configurable, abc.ABC):
    name: str

    @classmethod
    def from_config_identifier(
        cls, identifier: str, config: config.Config
    ) -> 'Rotator':
        options = config['rotate'][identifier].copy()
        rotator_class = rotators[options.pop('strategy')]
        return rotator_class.from_options(name=identifier, rotator=options)

    @classmethod
    @abc.abstractmethod
    def from_options(cls, name: str, rotator: dict) -> 'Rotator': ...

    @abc.abstractmethod
    def partition_backups(
        self, timestamp: datetime.datetime, backups: t.List[datetime.datetime]
    ) -> t.Iterable[t.Tuple[datetime.datetime, Verdict, str]]: ...

    def __str__(self) -> str:
        return self.name


rotators = registry.Registry[t.Type[Rotator]]()
