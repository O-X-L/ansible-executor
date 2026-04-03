from time import sleep
from pathlib import Path
from abc import ABC, abstractmethod
from json import dumps as json_dumps
from shutil import which as find_executable

from utils.debug import log
from utils.subps import process
from exceptions import ExecutionError
from runner_config import ExecutionConfig
from config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN


class ExecutorBase(ABC):
    def __init__(
            self,
            config: ExecutionConfig,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        self.config = config
        self.__secret_pipe_ssh_key = pipe_ssh_key
        self.__secret_pipe_connect_pass = pipe_connect_pass
        self.__secret_pipe_become_pass = pipe_become_pass
        self.__secret_pipe_vault_pass = pipe_vault_pass

        self.signal_stop = False
        self._engine_init()

    def _engine_init(self):
        pass

    def execute(self):
        log('Executing ansible-playbook')
        cmd = self.generate_engine_command()
        log(f'Command: {cmd}')

        # todo: subprocess execution
        # todo: process-monitor loop
        # todo: act on stop-signal
        # todo: add status-infos as attributes (for exec-status)

        sleep(30)

    @abstractmethod
    def generate_engine_command(self) -> list[str]:
        raise NotImplementedError('Engine command has to be implemented!')

    def generate_ansible_command(self) -> list[str]:
        # cleaned-up & simplified version of the official "ansible_runner.RunnerConfig.generate_ansible_command"
        # pylint: disable=R0912
        cmd = ['ansible-playbook']

        if self.config.inventory_files is not None:
            for i in self.config.inventory_files:
                cmd.extend(['-i', str(i)])

        if self.config.mode_check:
            cmd.append('--check')

        if self.config.mode_diff:
            cmd.append('--diff')

        if self.config.limit is not None:
            cmd.extend(['--limit', self.config.limit])

        if self.config.extra_vars is not None and len(self.config.extra_vars) > 0:
            extra_vars_list = []
            for k in self.config.extra_vars:
                extra_vars_list.append(f"\"{k}\":{json_dumps(self.config.extra_vars[k])}")

            cmd.extend(
                [
                    '-e',
                    f'{{{",".join(extra_vars_list)}}}'
                ]
            )

        if self.config.verbosity is not None:
            cmd.append(f'-{self.config.verbosity}')

        if self.config.tags is not None:
            cmd.extend(['--tags', self.config.tags])

        if self.config.skip_tags is not None:
            cmd.extend(['--skip-tags', self.config.skip_tags])

        if self.config.ssh_known_hosts_file is not None:
            cmd.extend([
                '-e',
                f"ansible_ssh_extra_args='-o UserKnownHostsFile={self.config.ssh_known_hosts_file}'",
            ])

        if self.config.connect_user is not None:
            cmd.extend(['--user', self.config.connect_user])

        if self.config.become_user is not None:
            cmd.extend(['--become-user', self.config.become_user])

        if self.config.vault_id is not None:
            for vault_id in self.config.vault_id:
                cmd.extend(['--vault-id', vault_id])

        cmd.extend(self._generate_secret_cmd_args())

        if self.config.cmd_args is not None:
            cmd.extend(self.config.cmd_args)

        cmd.append(str(self.config.playbook_file))
        return cmd

    def _generate_secret_cmd_args(self) -> list[str]:
        # pylint: disable=W0212
        args = []
        if self.config._ssh_key is not None:
            args.extend(['--private-key', str(self.__secret_pipe_ssh_key)])

        if self.config._connect_pass is not None:
            args.extend(['--connection-password-file', str(self.__secret_pipe_connect_pass)])

        if self.config._become_pass is not None:
            args.extend(['--become-password-file', str(self.__secret_pipe_become_pass)])

        if self.config._vault_pass is not None:
            args.extend(['--vault-password-file', str(self.__secret_pipe_vault_pass)])

        return args

    @abstractmethod
    def prepare_engine(self):
        raise NotImplementedError('Engine preparation has to be implemented!')


class ExecutorLocal(ExecutorBase):
    def generate_engine_command(self) -> list[str]:
        return self.generate_ansible_command()

    def prepare_engine(self):
        pass


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


class ExecutorContainerDocker(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_DOCKER


class ExecutorContainerPodman(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_PODMAN
