from pathlib import Path
from os import environ, getuid

LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
FALLBACK_CONTAINER_IMAGE = f'localhost/ansible-executor:{getuid()}'

DEFAULT_LOG_DIR = Path(f"{environ.get('HOME', '')}/.local/share/oxl-ansible-executor")

# names AND cli-executable
CONTAINER_ENGINE_DOCKER = 'docker'
CONTAINER_ENGINE_PODMAN = 'podman'
CONTAINER_ENGINES = (CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN)
