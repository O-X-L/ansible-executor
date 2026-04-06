from time import sleep
from pathlib import Path
from shutil import which as find_executable

from utils.debug import log
from utils.subps import process
from utils.util import get_random_str
from exceptions import ExecutionError
from config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN

from runner_executor_base import ExecutorBase
from runner_executor_command import AnsibleCommand


class ExecutorContainer(ExecutorBase):
    CONTAINER_ENGINE_NAME = None

    def _engine_init(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        if self.CONTAINER_ENGINE_NAME is None:
            raise NotImplementedError('CONTAINER_ENGINE_NAME has to be defined!')

        self.engine_executable = self._build_engine_executable()
        self._container_volumes = {
            str(self.config.playbook_dir): '/run/ansible',
        }
        self._ansible_command = AnsibleCommand(
            config=self.config,
            **self._build_paths_inside_container()
        )

    def _build_engine_executable(self) -> str:
        executable = find_executable(self.CONTAINER_ENGINE_NAME)
        if executable is not None:
            return executable

        return self.CONTAINER_ENGINE_NAME

    def _build_paths_inside_container(self) -> dict:
        container_files = {
            'pipe_ssh_key': f'/run/.{get_random_str(20)}',
            'pipe_pipe_connect_pass': f'/run/.{get_random_str(20)}',
            'pipe_pipe_become_pass': f'/run/.{get_random_str(20)}',
            'pipe_pipe_vault_pass': f'/run/.{get_random_str(20)}',
            'ssh_known_hosts_file': f'/run/.{get_random_str(20)}',
            'inventory_files': Path('/run/ansible_inventory'),
        }

        paths = {
            'pipe_ssh_key': container_files['pipe_ssh_key'],
            'pipe_connect_pass': container_files['pipe_connect_pass'],
            'pipe_become_pass': container_files['pipe_become_pass'],
            'pipe_vault_pass': container_files['pipe_vault_pass'],
            'inventory_files': [],
            'ssh_known_hosts_file': None,
        }

        for i, iv in enumerate(self.config.inventory_files):
            if str(iv).startswith('/'):
                iv_inside = container_files['inventory_files'] / str(i)
                self._container_volumes[str(iv)] = str(iv_inside)
                paths['inventory_files'].append(iv_inside)

            else:
                paths['inventory_files'].append(iv)

        if str(self.config.ssh_known_hosts_file).startswith('/'):
            ssh_kh_inside = container_files['ssh_known_hosts_file']
            self._container_volumes[str(self.config.ssh_known_hosts_file)] = ssh_kh_inside
            paths['ssh_known_hosts_file'].append(ssh_kh_inside)

        else:
            paths['ssh_known_hosts_file'].append(self.config.ssh_known_hosts_file)

        return paths

    def prepare_engine(self):
        self._pull_container_image()

    def _pull_container_image(self):
        # todo: log output to log-files
        image_pull = process(
            cmd=[self.engine_executable, 'image', 'pull', self.config.container_image],
            timeout_sec=3 * 60,
        )
        if not image_pull.failed:
            return

        image_query = process(
            cmd=[self.engine_executable, 'images', '-q', self.config.container_image],
            timeout_sec=10,
        )
        msg = f"Failed to pull container image: '{self.config.container_image}'"

        # only fail if the image does not exist and could not be pulled
        if image_query.stdout is None:
            raise ExecutionError(msg)

        if not self.config.silent:
            log(msg)

    def generate_ansible_command(self) -> list[str]:
        return self._ansible_command.generate()

    def generate_engine_command(self) -> list[str]:
        raise NotImplementedError('Engine command has to be implemented!')

    def _execute_command(self, cmd: list[str]) -> dict:
        sleep(30)
        return {}


class ExecutorContainerDocker(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_DOCKER


class ExecutorContainerPodman(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_PODMAN
