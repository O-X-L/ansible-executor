from time import sleep
from pathlib import Path
from threading import Thread
from shutil import which as find_executable
from signal import SIGINT, SIGKILL, SIGTERM

from utils.debug import log
from utils.subps import Process, ProcessArgs

from runner_executor_base import ExecutorBase
from runner_executor_command import AnsibleCommand


class ExecutorLocal(ExecutorBase):
    def _engine_init(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        self.engine_executable = self._build_engine_executable()
        self._ansible_command = AnsibleCommand(
            config=self.config,
            pipe_ssh_key=pipe_ssh_key,
            pipe_connect_pass=pipe_connect_pass,
            pipe_become_pass=pipe_become_pass,
            pipe_vault_pass=pipe_vault_pass,
            inventory_files=self.config.inventory_files,
            ssh_known_hosts_file=self.config.ssh_known_hosts_file,
        )

    @staticmethod
    def _build_engine_executable() -> str:
        executable = find_executable('ansible-playbook')
        if executable is not None:
            return executable

        return 'ansible-playbook'

    def generate_ansible_command(self) -> list[str]:
        return self._ansible_command.generate()

    def generate_engine_command(self) -> list[str]:
        cmd = self.generate_ansible_command()
        cmd[0] = self.engine_executable
        return cmd

    def prepare_engine(self):
        pass

    def _wait_for_process_to_finish(self):
        self.result = self.process.wait_until_finished()
        self.process.close()

    def _execute_command(self, cmd: list[str]):
        process_args = ProcessArgs(
            cwd=self.config.playbook_dir,
            timeout_sec=self.config.timeout_sec_run,
            env=self.config.env_vars,
            env_remove=self.config.env_vars_strip,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )
        self.process = Process(cmd=cmd, args=process_args)

        t = Thread(target=self._wait_for_process_to_finish)
        self.process_thread.append(t)
        t.start()

        self._process_control_loop()

    def _process_control_loop(self):
        while self.result is None:
            sleep(0.1)

            if self.signal_stop:
                log('Stopping execution')
                self.process.send_signal(SIGINT)
                sleep(2)
                if self.result is None:
                    self.process.send_signal(SIGKILL)

                sleep(2)
                if self.result is None:
                    self.process.send_signal(SIGTERM)

                break
