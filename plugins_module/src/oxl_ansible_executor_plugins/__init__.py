from os import path as os_path
from sys import path as sys_path

# pylint: disable=C0413
sys_path.append(os_path.dirname(os_path.abspath(__file__)))

from __script__ import get_path_callback
