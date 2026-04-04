from pathlib import Path
from shutil import which as find_executable

from utils.subps import process

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

    def _execute_command(self, cmd: list[str]) -> dict:
        # todo: allow process to be stopped via signal
        return process(
            cmd=cmd,
            cwd=self.config.playbook_dir,
            timeout_sec=self.config.timeout_sec_run,
            env=self.config.env_vars,
            env_remove=self.config.env_vars_strip,
        )
