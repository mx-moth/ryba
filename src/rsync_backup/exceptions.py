import dataclasses


@dataclasses.dataclass
class CommandError(Exception):
    message: str
    exit_code: int = 1


class ConfigError(CommandError):
    exit_code: int = 2


class RsyncError(CommandError):
    pass
