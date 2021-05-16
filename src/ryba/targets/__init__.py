from ._base import Backup, Target, TargetContext, target_types
from ._ssh import SSH, SSHContext

target_types['ssh'] = SSH

__all__ = [
    'Backup', 'Target', 'TargetContext', 'target_types',
    'SSH', 'SSHContext',
]
