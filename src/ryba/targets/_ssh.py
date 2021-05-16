import contextlib
import functools
import pathlib
import shlex
import sys
import types
import typing as t

import attr
import paramiko.config
import spur

from .. import exceptions, logging
from . import _base

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, kw_only=True)
class SSH(_base.Target):
    name: str
    hostname: str = attr.ib()
    username: t.Optional[str] = None
    port: t.Optional[int] = None
    path: pathlib.Path = pathlib.Path('/')

    @hostname.default
    def _default_hostname(self) -> str:
        return self.name

    @classmethod
    def from_options(cls, name: str, config: dict) -> "SSH":
        try:
            return cls(name=name, **config)
        except TypeError as exc:
            raise exceptions.ConfigError(str(exc))

    def rsync_arguments(self, destination: pathlib.Path) -> t.Tuple[str, t.List[str]]:
        options = []

        ssh_options = []
        if self.port:
            ssh_options += ['-p', str(self.port)]
        if ssh_options:
            options += ['-e', shlex.join(['ssh'] + ssh_options)]

        if self.username:
            target_str = f'{self.username}@{self.hostname}:{destination}'
        else:
            target_str = f'{self.hostname}:{destination}'

        return (target_str, options)

    def connect(self) -> 'SSHContext':
        return SSHContext(target=self)

    def __str__(self) -> str:
        return self.name


@attr.s(auto_attribs=True, kw_only=True)
class SSHContext(_base.TargetContext):
    target: SSH

    @functools.cached_property
    def _stack(self) -> contextlib.ExitStack:
        return contextlib.ExitStack()

    @functools.cached_property
    def client(self) -> spur.SshShell:
        ssh_config_path = pathlib.Path('~/.ssh/config').expanduser()
        ssh_config = paramiko.config.SSHConfig.from_path(str(ssh_config_path))
        host_config = ssh_config.lookup(self.target.hostname)
        return spur.SshShell(
            hostname=host_config.get('hostname'),
            username=self.target.username or host_config.get('username'),
            port=self.target.port or host_config['port'],
        )

    @functools.cached_property
    def sftp(self) -> paramiko.SFTPClient:
        return t.cast(paramiko.SFTPClient, self.client._open_sftp_client())

    def __enter__(self) -> 'SSHContext':
        self._stack.__enter__
        self._stack.enter_context(self.client)
        return self

    def __exit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[types.TracebackType],
    ) -> None:
        self._stack.__exit__(exc_type, exc_value, traceback)
        with contextlib.suppress(AttributeError):
            del self.sftp
        del self.client

    def make_path(self, path: pathlib.Path) -> pathlib.Path:
        if path.is_absolute():
            path = path.relative_to('/')
        return self.target.path / path

    def execute(self, cmd: t.List[str]) -> None:
        logger.log(logging.DEBUG, logging.command(cmd, hostname=self.target.hostname))
        self.client.run(cmd, stdout=sys.stdout, stderr=sys.stderr)

    def exists(self, path: pathlib.Path) -> bool:
        result = self.client.run(['test', '-e', str(self.make_path(path))], allow_error=True)
        return t.cast(int, result.return_code) == 0

    def read_file(self, path: pathlib.Path) -> bytes:
        with self.sftp.open(str(self.make_path(path)), 'rb') as f:
            return t.cast(bytes, f.read())

    def write_file(self, path: pathlib.Path, contents: bytes) -> None:
        with self.sftp.open(str(self.make_path(path)), 'wb') as f:
            f.write(contents)

    def list_directory(self, path: pathlib.Path) -> t.List[str]:
        return self.sftp.listdir(str(self.make_path(path)))
