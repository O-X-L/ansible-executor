class ConfigError(ValueError):
    pass


class SetupError(ConfigError):
    pass


class PreparationError(EnvironmentError):
    pass


class ExecutionError(EnvironmentError):
    pass
