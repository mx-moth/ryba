import typing as t

T = t.TypeVar("T")


class Registry(t.Generic[T]):
    _registry: dict[str, T]

    def __init__(self) -> None:
        self._registry = {}

    def register(self, name: str) -> t.Callable[[T], T]:
        def _decorator(item: T) -> T:
            self[name] = item
            return item
        return _decorator

    def __setitem__(self, name: str, item: T) -> None:
        self._registry[name] = item

    def __getitem__(self, key: str) -> T:
        return self._registry[key]
