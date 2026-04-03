from shutil import which as find_executable

from utils.subps import process

from runner_executor_base import ExecutorBase


class ExecutorLocal(ExecutorBase):
    def _engine_init(self):
        self.engine_executable = self._get_engine_executable()

    @staticmethod
    def _get_engine_executable() -> str:
        executable = find_executable('ansible-playbook')
        if executable is not None:
            return executable

        return 'ansible-playbook'

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
