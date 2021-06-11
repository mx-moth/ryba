import pathlib
import subprocess
import types
import typing as t

import attr

from .. import exceptions, logging
from . import _base

logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, kw_only=True)
class Local(_base.Target):
    name: str
    path: pathlib.Path

    @classmethod
    def from_options(cls, name: str, config: dict) -> "Local":
        path = pathlib.Path(config.pop('path')).expanduser()
        try:
            return cls(name=name, path=path)
        except TypeError as exc:
            raise exceptions.ConfigError(str(exc))

    def rsync_arguments(self, destination: pathlib.Path) -> t.Tuple[str, t.List[str]]:
        options: t.List[str] = []
        target_str = str(self.path / destination)
        return (target_str, options)

    def connect(self) -> 'LocalContext':
        return LocalContext(target=self)

    def __str__(self) -> str:
        return self.name


@attr.s(auto_attribs=True, kw_only=True)
class LocalContext(_base.TargetContext):
    target: Local

    def __enter__(self) -> "LocalContext":
        return self

    def __exit__(
        self,
        exc_type: t.Optional[t.Type[BaseException]],
        exc_value: t.Optional[BaseException],
        traceback: t.Optional[types.TracebackType],
    ) -> None:
        pass

    def make_path(self, path: pathlib.Path) -> pathlib.Path:
        """
        Take an absolute path and append it to the base path for this target.
        Useful for mounted media, for example.
        """
        if path.is_absolute():
            path = path.relative_to('/')
        return self.target.path / path

    def execute(self, cmd: t.List[str]) -> None:
        """Run a command on the target."""
        logger.log(logging.DEBUG, logging.command(cmd))
        subprocess.check_call(cmd)

    def exists(self, path: pathlib.Path) -> bool:
        return self.make_path(path).exists()

    def read_file(self, path: pathlib.Path) -> bytes:
        return self.make_path(path).read_bytes()

    def write_file(self, path: pathlib.Path, contents: bytes) -> None:
        self.make_path(path).write_bytes(contents)

    def list_directory(self, path: pathlib.Path) -> t.List[str]:
        return [p.name for p in sorted(self.make_path(path).iterdir())]
