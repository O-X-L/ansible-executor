from pathlib import Path


def get_path_callback() -> str:
    return str(Path(__file__).parent / 'callback')


def print_path_callback():
    print(get_path_callback())
