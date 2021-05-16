import collections
import datetime
import typing as t

import attr

from .. import targets
from ._base import Rotator, Verdict


class _SupportsLessThan(t.Protocol):
    def __lt__(self, __other: t.Any) -> bool: ...


TValue = t.TypeVar("TValue", bound=_SupportsLessThan)
Count = t.Union[int, t.Literal["all"]]


@attr.s(auto_attribs=True, kw_only=True)
class Bucket(t.Generic[TValue]):
    name: str
    count: Count
    decider: t.Callable[[TValue, TValue], TValue]
    grouper: t.Callable[[TValue], t.Hashable]
    _groups: t.Dict[t.Hashable, TValue] = attr.ib(factory=dict)

    def add(self, value: TValue) -> None:
        group: t.Hashable = self.grouper(value)
        if group in self._groups:
            decider = self.decider(value, self._groups[group])
            self._groups[group] = decider
        else:
            self._groups[group] = value

    def get_winners(self) -> t.List[TValue]:
        winners = sorted(self._groups.values(), reverse=True)
        if self.count == 'all':
            return winners
        else:
            return winners[:self.count]


def _year(bucket: targets.Backup) -> int:
    t = bucket.timestamp
    return t.year


def _month(bucket: targets.Backup) -> t.Tuple[int, int]:
    t = bucket.timestamp
    return t.year, t.month


def _week(bucket: targets.Backup) -> t.Tuple[int, int]:
    t = bucket.timestamp
    return t.isocalendar()[:2]


def _day(bucket: targets.Backup) -> t.Tuple[int, int, int]:
    t = bucket.timestamp
    return t.year, t.month, t.day


def _hour(bucket: targets.Backup) -> t.Tuple[int, int, int, int]:
    t = bucket.timestamp
    return t.year, t.month, t.day, t.hour


@attr.s(auto_attribs=True, kw_only=True)
class DateBucket(Rotator):
    """
    All backups are sorted in to buckets. If it doesn't fit in the bucket, it
    is sorted into the next bucket. If it doesn't fit in any
    bucket, it is discarded.
    """
    name: str

    #: How many hourly backups to keep.
    hour: t.Optional[Count] = None
    #: How many daily backups to keep.
    day: t.Optional[Count] = None
    #: How many weekly backups to keep
    week: t.Optional[Count] = None
    #: How many monthly (30 day window) backups to keep
    month: t.Optional[Count] = None
    #: How many yearly backups to keep
    year: t.Optional[Count] = None

    prefer_newest: bool = False

    @classmethod
    def from_options(cls, name: str, rotator: dict) -> 'DateBucket':
        return cls(name=name, **rotator)

    def rotate_backups(
        self,
        timestamp: datetime.datetime,
        backups: t.List[targets.Backup],
    ) -> t.Iterable[t.Tuple[targets.Backup, Verdict, str]]:
        winners = self.get_winners(backups)
        for backup_date in backups:
            if backup_date in winners:
                verdict = Verdict.keep
                explanation = f"Kept by buckets: {', '.join(winners[backup_date])}"
            else:
                verdict = Verdict.drop
                explanation = "Not kept by any bucket"
            yield backup_date, verdict, explanation

    def get_winners(self, backups: t.List[targets.Backup]) -> t.Dict[targets.Backup, t.List[str]]:
        backups = sorted(backups)
        decider = max if self.prefer_newest else min

        buckets: t.List[Bucket[targets.Backup]] = []
        if self.year:
            buckets.append(Bucket(name="Year", count=self.year, decider=decider, grouper=_year))
        if self.month:
            buckets.append(Bucket(name="Month", count=self.month, decider=decider, grouper=_month))
        if self.week:
            buckets.append(Bucket(name="Week", count=self.week, decider=decider, grouper=_week))
        if self.day:
            buckets.append(Bucket(name="Day", count=self.day, decider=decider, grouper=_day))
        if self.hour:
            buckets.append(Bucket(name="Hour", count=self.hour, decider=decider, grouper=_hour))

        for backup in backups:
            for bucket in buckets:
                bucket.add(backup)

        winners: t.Dict[targets.Backup, t.List[str]] = collections.defaultdict(list)
        for bucket in buckets:
            for nth, to_keep in enumerate(bucket.get_winners(), start=1):
                winners[to_keep].append(f"{bucket.name} ({nth})")

        winners[backups[-1]].append("Latest")

        return winners
