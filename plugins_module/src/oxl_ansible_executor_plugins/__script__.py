from pathlib import Path


def get_path_callback():
    print(Path(__file__).parent / 'callback')
