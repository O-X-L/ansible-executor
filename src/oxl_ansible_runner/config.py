from os import environ
from pathlib import Path

LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S %z'
# todo: change to locally built image
#   (build-arg UID or executing user because of mount/volume file-privileges..)
FALLBACK_CONTAINER_IMAGE = 'oxlorg/ansible-executor'

DEFAULT_LOG_DIR = Path(f"{environ.get('HOME', '')}/.local/share/oxl-ansible-executor")

# names AND cli-executable
CONTAINER_ENGINE_DOCKER = 'docker'
CONTAINER_ENGINE_PODMAN = 'podman'
CONTAINER_ENGINES = (CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN)
