from pathlib import Path
from sys import path as sys_path

# pylint: disable=C0413
sys_path.append(str(Path(__file__).parent.parent))

from oxl_ansible_executor_plugins.__script__ import get_path_callback
