from pathlib import Path
from copy import deepcopy
from time import sleep, time
from threading import Thread
from abc import ABC, abstractmethod
from signal import SIGINT, SIGKILL, SIGTERM

from utils.debug import log
from utils.subps import ProcessResult
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
        self.config: ExecutionConfig = config

        self.process_thread = []
        self.process = None
        self.result: ProcessResult = None
        self.signal_stop = False
        self.time_finish: int = -1
        self.timed_out: bool = False
        self.command: list[str] = None
        self.ansible_command: list[str] = None

        self._pipe_ssh_key = pipe_ssh_key
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
        if self.config.debug:
            log('Executing ansible-playbook')

        self.config.env_vars = self.config.add_to_dict(
            self.config.env_vars,
            key='ANSIBLE_FORCE_COLOR',
            value='1' if self.config.output_color else '0',
        )

        cmd = self.generate_engine_command()
        self.command = cmd
        if self.config.debug:
            log(f'Command: {cmd}')

        self._create_process(cmd)

        t = Thread(target=self._wait_for_process_to_finish)
        self.process_thread.append(t)
        t.start()

        self._process_control_loop()

    def _wait_for_process_to_finish(self):
        self.process.wait_until_finished()
        self._set_process_result()
        self.process.close()

    def _set_process_result(self):
        if self.result is None:
            self.result = deepcopy(self.process.result)

        if self.time_finish == -1:
            self.time_finish = int(time())

    def _process_control_loop(self):
        time_start = time()

        while self.result is None:
            sleep(0.1)

            if (time() - self.config.timeout_sec_run) > time_start:
                if self.config.debug:
                    log('Executor timeout reached')

                self.signal_stop = True
                self.timed_out = True

            if self.process.result.rc != -1 and self.result is None:
                self._set_process_result()
                break

            if self.signal_stop:
                if self.config.debug:
                    log('Stopping execution')

                # try to end ansible 'gracefully'
                self._send_signal_to_ansible(SIGINT)
                sleep(2)

                if self.result is None:
                    self._send_signal_to_ansible(SIGKILL)
                    sleep(2)

                # kill the actual subprocess
                if self.result is None:
                    self.process.send_signal(SIGKILL)
                    sleep(2)

                if self.result is None:
                    self.process.send_signal(SIGTERM)

                break

        self._set_process_result()

    @abstractmethod
    def _create_process(self, cmd: list[str]):
        raise NotImplementedError('Command-execution has to be implemented!')

    @abstractmethod
    def _send_signal_to_ansible(self, signal: int):
        raise NotImplementedError('Sending signals to ansible has to be implemented!')

    @abstractmethod
    def generate_engine_command(self) -> list[str]:
        raise NotImplementedError('Engine command has to be implemented!')

    @abstractmethod
    def prepare_engine(self):
        raise NotImplementedError('Engine preparation has to be implemented!')
