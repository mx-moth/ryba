from ._base import Rotator, Verdict, rotators
from ._date import DateBucket
from ._simple import KeepAll, KeepLatest

__all__ = ['Verdict', 'Rotator', 'rotators', 'DateBucket', 'KeepAll', 'KeepLatest']

rotators['all'] = KeepAll
rotators['latest'] = KeepLatest
rotators['date-bucket'] = DateBucket
