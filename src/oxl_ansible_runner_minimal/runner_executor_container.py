from time import sleep
from shutil import which as find_executable

from utils.debug import log
from utils.subps import process
from exceptions import ExecutionError
from config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN

from runner_executor_base import ExecutorBase


class ExecutorContainer(ExecutorBase):
    CONTAINER_ENGINE_NAME = None

    def _engine_init(self):
        if self.CONTAINER_ENGINE_NAME is None:
            raise NotImplementedError('CONTAINER_ENGINE_NAME has to be defined!')

        self.engine_executable = self._get_engine_executable()

    def _get_engine_executable(self) -> str:
        executable = find_executable(self.CONTAINER_ENGINE_NAME)
        if executable is not None:
            return executable

        return self.CONTAINER_ENGINE_NAME

    def prepare_engine(self):
        self._pull_container_image()

    def _pull_container_image(self):
        # todo: log output to log-files
        image_pull = process(
            cmd=[self.engine_executable, 'image', 'pull', self.config.container_image],
            timeout_sec=3 * 60,
        )
        if image_pull['rc'] == 0:
            return

        image_query = process(
            cmd=[self.engine_executable, 'images', '-q', self.config.container_image],
            timeout_sec=10,
        )
        msg = f"Failed to pull container image: '{self.config.container_image}'"

        # only fail if the image does not exist and could not be pulled
        if image_query['stdout'] is None:
            raise ExecutionError(msg)

        log(msg)

    def generate_engine_command(self) -> list[str]:
        raise NotImplementedError('Engine command has to be implemented!')

    def _execute_command(self, cmd: list[str]) -> dict:
        sleep(30)
        return {}


class ExecutorContainerDocker(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_DOCKER


class ExecutorContainerPodman(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_PODMAN
