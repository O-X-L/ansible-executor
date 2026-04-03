from os import environ
from pathlib import Path
from functools import cache
from tempfile import mkdtemp

from oxl_utils.ps import process as oxl_utils_process

from utils.debug import log


# pylint: disable=R0914
def process(
        cmd: list[str], cwd: Path = None, timeout_sec: int = None, shell: bool = False,
        env: dict = None, env_remove: list = None, stdin: str = None,
) -> dict:
    # returns: dict containing rc[int],stdout[str],stderr[str]
    if not isinstance(cmd, list):
        raise TypeError('Command has to be of type list[str] !')

    if cwd is None:
        cwd = Path(mkdtemp(prefix='ar_'))

    log(msg=f"Executing command: '{' '.join(cmd)}'")

    # merge provided env with current env and hide secrets
    env_full = environ.copy()
    if env is not None:
        env_full = {**env_full, **env}

    if env_remove is not None:
        for env_var in env_remove:
            if env_var in env_full:
                env_full.pop(env_var)

    return oxl_utils_process(
        cmd=cmd, timeout_sec=timeout_sec, shell=shell, cwd=cwd, env=env_full, stdin=stdin,
        env_inherit=False, empty_none=False, timeout_shell=False,
    )


@cache
def process_cache(
        cmd: list[str], cwd: Path = None, timeout_sec: int = None, shell: bool = False,
        env: dict = None, env_remove: list = None,
) -> dict:
    # read-only commands which results can be cached
    return process(cmd=cmd, timeout_sec=timeout_sec, shell=shell, cwd=cwd, env=env, env_remove=env_remove)
