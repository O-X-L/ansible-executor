from string import digits, ascii_letters
from random import choice as random_choice


def get_random_str(l: int = 50) -> str:
    return ''.join(random_choice(ascii_letters + digits) for _ in range(l))
