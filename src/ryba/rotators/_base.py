import abc
import datetime
import enum
import typing as t

from .. import config, registry, targets

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

    def should_rotate(self) -> t.Union[t.Literal[True], str]:
        """
        Should backup rotation be attempted? Return either the value True, or
        a string explanation of why not.
        """
        return True

    @abc.abstractmethod
    def rotate_backups(
        self, timestamp: datetime.datetime, backups: t.List[targets.Backup]
    ) -> t.Iterable[t.Tuple[targets.Backup, Verdict, str]]:
        """
        Decide how to rotate a set of backups. `timestamp` is the current
        timestamp, while `backups` is a list of backup timestamps.

        Implementations should return a tuple of `(backup, verdict, reason)`
        for each backup timestamp, where `verdict` is `Verdict.keep` or
        `Verdict.drop`, and `reason` is a short explanation of the verdict.
        """

    def __str__(self) -> str:
        return self.name


rotators = registry.Registry[t.Type[Rotator]]()
