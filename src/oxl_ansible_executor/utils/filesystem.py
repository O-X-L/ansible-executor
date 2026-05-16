from pathlib import Path
from typing import Callable
from os import open as open_file
from os import remove as remove_file

from utils.subps import process
from utils.util import get_random_str


def _open_file_0600(path: (str, Path), flags):
    return open_file(path, flags, 0o600)


def _open_file_0640(path: (str, Path), flags):
    return open_file(path, flags, 0o640)


def _open_file_0660(path: (str, Path), flags):
    return open_file(path, flags, 0o660)


def _open_file_0644(path: (str, Path), flags):
    return open_file(path, flags, 0o644)


def _open_file_0664(path: (str, Path), flags):
    return open_file(path, flags, 0o664)


FILE_WRITE_MODES = {
    0o600: _open_file_0600,
    0o640: _open_file_0640,
    0o644: _open_file_0644,
    0o660: _open_file_0660,
    0o664: _open_file_0664,
}

def get_file_opener_from_mode(file_mode: int) -> Callable:
    return FILE_WRITE_MODES.get(file_mode, _open_file_0640)


def write_file_with_mode(file: (str, Path), content: str, file_mode: int):
    file = Path(file)
    if not file.parent.is_dir():
        file.parent.mkdir(mode=0o750, parents=True, exist_ok=True)

    mode = 'w'
    if file.is_file():
        mode = 'a'

    opener = get_file_opener_from_mode(file_mode)

    with open(file, mode, encoding='utf-8', opener=opener) as _file:
        _file.write(content)


def overwrite_and_delete_file(file: (str, Path, None)):
    if file is None:
        return

    if not isinstance(file, Path):
        file = Path(file)

    if not file.is_file():
        return

    for _ in range(3):
        write_file_with_mode(
            file=file,
            content=get_random_str(),
            file_mode=0o600,
        )

    remove_file(file)


def rm_dir(path: (str, Path)) -> int:
    return process(f'rm -rf {path}').rc
