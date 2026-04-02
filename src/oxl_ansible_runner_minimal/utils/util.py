from random import choice as random_choice
from string import digits, ascii_letters, punctuation


def get_random_str(l: int = 50) -> str:
    return ''.join(random_choice(ascii_letters + digits + punctuation) for _ in range(l))
