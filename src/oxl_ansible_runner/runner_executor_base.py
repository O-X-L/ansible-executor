from pathlib import Path
from abc import ABC, abstractmethod

from utils.debug import log
from runner_config import ExecutionConfig


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

        self.process_thread = []
        self.process = None
        self.result = None
        self.signal_stop = False

        self._engine_init(
            pipe_ssh_key=pipe_ssh_key,
            pipe_connect_pass=pipe_connect_pass,
            pipe_become_pass=pipe_become_pass,
            pipe_vault_pass=pipe_vault_pass,
        )

    def _engine_init(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        pass

    def execute(self):
        log('Executing ansible-playbook')
        cmd = self.generate_engine_command()
        log(f'Command: {cmd}')
        log(f'Log files: {self.config.log_stdout_file} | {self.config.log_stderr_file}')

        # result = self._execute_command(cmd)
        self._execute_command(cmd)
        # todo: subprocess execution
        # todo: process-monitor loop
        # todo: act on stop-signal
        # todo: add status-infos as attributes (for exec-status)

    @abstractmethod
    def _execute_command(self, cmd: list[str]) -> dict:
        raise NotImplementedError('Command-execution has to be implemented!')

    @abstractmethod
    def generate_ansible_command(self) -> list[str]:
        raise NotImplementedError('Command-generation has to be implemented!')

    @abstractmethod
    def generate_engine_command(self) -> list[str]:
        raise NotImplementedError('Engine command has to be implemented!')

    @abstractmethod
    def prepare_engine(self):
        raise NotImplementedError('Engine preparation has to be implemented!')
