import abc
import collections
import datetime
import itertools
import pathlib
import typing as t

import toml
import xdg


def get_default_config_path() -> pathlib.Path:
    return xdg.xdg_config_home() / 'ryba' / 'config.toml'


class Configurable(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def from_config_identifier(cls, identifier: str, config: 'Config') -> 'Configurable': ...


class Singleton:
    pass


TSingleton = t.TypeVar('TSingleton', bound=Singleton)
TConfigurable = t.TypeVar('TConfigurable', bound=Configurable)


class Config:

    DEFAULTS = {
        'ryba': {
            'verbosity': 1,
        }
    }

    _config: t.Mapping[str, t.Any]
    _configurable_cache: t.MutableMapping[t.Type[Configurable], t.Mapping[str, Configurable]]
    _singleton_cache: t.MutableMapping[t.Type[Singleton], Singleton]

    def __init__(self, *configs: t.Mapping[str, t.Any]):
        self._config = NestedChainMap(*configs)
        self._configurable_cache = collections.defaultdict(dict)
        self._singleton_cache = {}

    @classmethod
    def from_file(cls, file_path: pathlib.Path) -> "Config":
        return cls(toml.load(file_path), cls.DEFAULTS)

    @classmethod
    def defaults(cls) -> "Config":
        return cls(cls.DEFAULTS)

    def __getitem__(self, key: t.Any) -> t.Any:
        return self._config[key]

    @t.overload
    def get(self, item: t.Union[t.Type[TConfigurable], str]) -> TConfigurable: ...
    @t.overload
    def get(self, item: t.Type[TSingleton]) -> TSingleton: ...

    def get(
        self,
        item: t.Union[t.Union[t.Type[TConfigurable], str], t.Type[TSingleton]],
    ) -> t.Union[TConfigurable, TSingleton]:
        if isinstance(item, tuple):
            item = t.cast(t.Union[t.Type[TConfigurable], str], item)
            cls, identifier = item
            cls_cache = t.cast(t.MutableMapping[str, Configurable], self._configurable_cache[cls])
            try:
                return cls_cache[identifier]
            except KeyError:
                value = cls.from_config_identifier(identifier, self)
                self.set(item, value)
                return value

        if isinstance(item, type) and issubclass(item, Singleton):
            return t.cast(TSingleton, self._singleton_cache[item])

        raise NotImplementedError(f"Can't get config of {item!r}")

    @t.overload
    def set(self, item: t.Union[t.Type[TConfigurable], str], value: TConfigurable) -> None: ...
    @t.overload
    def set(self, item: t.Type[TSingleton], value: TSingleton) -> None: ...

    def set(
        self,
        item: t.Union[t.Union[t.Type[TConfigurable], str], t.Type[TSingleton]],
        value: t.Union[TConfigurable, TSingleton],
    ) -> None:
        if isinstance(item, tuple):
            cls, identifier = item
            cls_cache = t.cast(t.MutableMapping[str, TConfigurable], self._configurable_cache[cls])
            cls_cache[identifier] = value

        elif isinstance(item, type) and issubclass(item, Singleton):
            self._singleton_cache[item] = t.cast(TSingleton, value)

        return None


class NestedChainMap(collections.ChainMap):
    def __getitem__(self, key: t.Any) -> t.Union[str, int, datetime.datetime, t.Mapping, list]:
        items = (m[key] for m in self.maps if key in m)
        try:
            prototype = next(items)
        except StopIteration:
            raise KeyError(key)

        if isinstance(prototype, t.Mapping):
            _items = list(items)
            if len(_items) == 0:
                return prototype

            return NestedChainMap(prototype, *items)

        if isinstance(prototype, t.Iterable):
            return list(itertools.chain(prototype, *items))

        return prototype  # type: ignore
