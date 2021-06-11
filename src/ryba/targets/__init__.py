from ._base import Backup, Target, TargetContext, target_types
from ._local import Local, LocalContext
from ._ssh import SSH, SSHContext

target_types['local'] = Local
target_types['ssh'] = SSH

__all__ = [
    'Backup', 'Target', 'TargetContext', 'target_types',
    'Local', 'LocalContext',
    'SSH', 'SSHContext',
]
