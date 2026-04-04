from os import environ
from pathlib import Path

LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
FALLBACK_CONTAINER_IMAGE = 'oxlorg/ansible-executor'

DEFAULT_LOG_DIR = Path(f"{environ.get('HOME', '')}/.local/share/oxl-ansible-runner")

# names AND cli-executable
CONTAINER_ENGINE_DOCKER = 'docker'
CONTAINER_ENGINE_PODMAN = 'podman'
CONTAINER_ENGINES = (CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN)
