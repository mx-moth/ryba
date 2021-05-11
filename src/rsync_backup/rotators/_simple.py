import datetime
import typing as t

import attr

from .. import exceptions
from ._base import Rotator, Verdict


@attr.s(auto_attribs=True, kw_only=True)
class KeepAll(Rotator):
    name: str

    @classmethod
    def from_options(cls, name: str, rotator: dict) -> 'KeepAll':
        if rotator != {}:
            raise exceptions.ConfigError("'all' stragegy does not take any options")
        return cls(name=name)

    def partition_backups(
        self, timestamp: datetime.datetime, backups: t.List[datetime.datetime]
    ) -> t.Iterable[t.Tuple[datetime.datetime, Verdict, str]]:
        return ((backup, Verdict.keep, "Keep all backups") for backup in backups)


@attr.s(auto_attribs=True, kw_only=True)
class KeepLatest(Rotator):
    name: str
    count: int

    @classmethod
    def from_options(cls, name: str, rotator: dict) -> 'KeepLatest':
        return cls(name=name, **rotator)

    def partition_backups(
        self, timestamp: datetime.datetime, backups: t.List[datetime.datetime]
    ) -> t.Iterable[t.Tuple[datetime.datetime, Verdict, str]]:
        backups = sorted(backups)
        to_drop = backups[:-self.count]
        to_keep = backups[-self.count:]
        drop_reason = f"Not in the {self.count} latest backups"
        keep_reason = f"Keep latest {self.count}"
        yield from ((backup, Verdict.drop, drop_reason) for backup in to_drop)
        yield from ((backup, Verdict.keep, keep_reason) for backup in to_keep)
