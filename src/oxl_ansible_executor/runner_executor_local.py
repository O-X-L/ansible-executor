from pathlib import Path
from shutil import which as find_executable

from oxl_ansible_executor.utils.subps import Process, ProcessArgs

from oxl_ansible_executor.config import ENV_ANSIBLE_CALLBACK_PLUGINS
from oxl_ansible_executor.runner_executor_base import ExecutorBase
from oxl_ansible_executor.runner_executor_command import AnsibleCommand, wrap_cmd_in_ssh_agent


class ExecutorLocal(ExecutorBase):
    def _engine_init(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        self.engine_executable = self._build_engine_executable()
        self._ansible_command_generator = AnsibleCommand(
            config=self.config,
            pipe_connect_pass=pipe_connect_pass,
            pipe_become_pass=pipe_become_pass,
            pipe_vault_pass=pipe_vault_pass,
            inventory_files=self.config.inventory_files,
            ssh_known_hosts_file=self.config.ssh_known_hosts_file,
        )
        self.ansible_command = self._ansible_command_generator.generate()

    @staticmethod
    def _build_engine_executable() -> str:
        executable = find_executable('ansible-playbook')
        if executable is not None:
            return executable

        return 'ansible-playbook'

    def generate_engine_command(self) -> list[str]:
        cmd = self.ansible_command.copy()
        cmd[0] = self.engine_executable
        # pylint: disable=W0212
        if self.config._ssh_key is not None:
            return wrap_cmd_in_ssh_agent(cmd=cmd, ssh_key_file=self._pipe_ssh_key)

        return cmd

    def _prepare_engine(self):
        if self.config.stats_recap or self.config.stats_live:
            self._add_stats_plugins_path()

    def _add_stats_plugins_path(self):
        try:
            # pylint: disable=C0415
            from oxl_ansible_executor_plugins import get_path_callback

        except (ImportError, ModuleNotFoundError):
            return

        path_stats_callback = get_path_callback()
        ansible_callback_paths = []
        if self.config.env_vars is not None and ENV_ANSIBLE_CALLBACK_PLUGINS in self.config.env_vars:
            ansible_callback_paths = self.config.env_vars[ENV_ANSIBLE_CALLBACK_PLUGINS].split(':')

        if path_stats_callback not in ansible_callback_paths:
            ansible_callback_paths.append(path_stats_callback)

        self.config.env_vars = self.config.add_to_dict(
            self.config.env_vars,
            key=ENV_ANSIBLE_CALLBACK_PLUGINS,
            value=':'.join(ansible_callback_paths),
        )

    def _create_process(self, cmd: list[str]):
        process_args = ProcessArgs(
            cwd=self.config.playbook_dir,
            timeout_sec=self.config.timeout_sec_run,
            env=self.config.env_vars,
            env_inherit=True,
            env_remove=self.config.env_vars_strip,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )
        self.process = Process(cmd=cmd, args=process_args)

    def _send_signal_to_ansible(self, signal: int):
        self.process.send_signal(signal)
