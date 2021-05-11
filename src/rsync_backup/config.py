import abc
import collections
import pathlib
import typing as t

import toml
import xdg


def get_default_config_path() -> pathlib.Path:
    return xdg.xdg_config_home() / 'python-rsync-backup' / 'config.toml'


class Configurable(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_config_identifier(cls, identifier: str, config: 'Config') -> 'Configurable': ...


TConfigurable = t.TypeVar('TConfigurable', bound=Configurable)


class Config:
    _config: t.Mapping[str, t.Any]
    _configurable_cache: t.MutableMapping[t.Type[Configurable], t.Mapping[str, Configurable]]

    def __init__(self, config: t.Mapping[str, t.Any]):
        self._config = config
        self._configurable_cache = collections.defaultdict(dict)

    @classmethod
    def from_file(cls, file_path: pathlib.Path) -> "Config":
        return cls(toml.load(file_path))

    @classmethod
    def defaults(cls) -> "Config":
        return cls({})

    def __getitem__(self, key: t.Any) -> t.Any:
        return self._config[key]

    def get(self, cls: t.Type[TConfigurable], identifier: str) -> TConfigurable:
        cls_cache = t.cast(t.MutableMapping[str, TConfigurable], self._configurable_cache[cls])
        try:
            return cls_cache[identifier]
        except KeyError:
            value = t.cast(TConfigurable, cls.from_config_identifier(identifier, self))
            cls_cache[identifier] = value
            return value
