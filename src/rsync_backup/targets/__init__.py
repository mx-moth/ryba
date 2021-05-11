from ._base import Target, TargetContext, target_types
from ._ssh import SSH, SSHContext

target_types['ssh'] = SSH

__all__ = [
    'Target', 'TargetContext', 'target_types',
    'SSH', 'SSHContext',
]
