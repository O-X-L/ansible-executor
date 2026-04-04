from pathlib import Path
from json import dumps as json_dumps

from runner_config import ExecutionConfig


class AnsibleCommand:
    # pylint: disable=R0913,R0917
    def __init__(
            self,
            config: ExecutionConfig,

            pipe_ssh_key: (Path, None),
            pipe_connect_pass: (Path, None),
            pipe_become_pass: (Path, None),
            pipe_vault_pass: (Path, None),

            inventory_files: list[Path|None],
            ssh_known_hosts_file: (Path, None),
    ):
        self.config = config

        # separate from ExecutionConfig because paths differ inside container
        self.inventory_files = inventory_files
        self.ssh_known_hosts_file = ssh_known_hosts_file

        self.__secret_pipe_ssh_key = pipe_ssh_key
        self.__secret_pipe_connect_pass = pipe_connect_pass
        self.__secret_pipe_become_pass = pipe_become_pass
        self.__secret_pipe_vault_pass = pipe_vault_pass

    def _generate_args_auth(self) -> list[str]:
        # pylint: disable=W0212
        args = []
        if self.config.connect_user is not None:
            args.extend(['--user', self.config.connect_user])

        if self.config._ssh_key is not None and self.__secret_pipe_ssh_key is not None:
            args.extend(['--private-key', str(self.__secret_pipe_ssh_key)])

        if self.config._connect_pass is not None and self.__secret_pipe_connect_pass is not None:
            args.extend(['--connection-password-file', str(self.__secret_pipe_connect_pass)])

        if self.ssh_known_hosts_file is not None:
            args.extend([
                '-e',
                f"ansible_ssh_extra_args='-o UserKnownHostsFile={self.ssh_known_hosts_file}'",
            ])

        if self.config.become_user is not None:
            args.extend(['--become-user', self.config.become_user])

        if self.config._become_pass is not None and self.__secret_pipe_become_pass is not None:
            args.extend(['--become-password-file', str(self.__secret_pipe_become_pass)])

        if self.config._vault_pass is not None and self.__secret_pipe_vault_pass is not None:
            args.extend(['--vault-password-file', str(self.__secret_pipe_vault_pass)])

        if self.config.vault_id is not None:
            for vault_id in self.config.vault_id:
                args.extend(['--vault-id', vault_id])

        return args

    def _generate_args_basic(self) -> list[str]:
        args = []
        if self.inventory_files is not None:
            for i in self.inventory_files:
                args.extend(['-i', str(i)])

        if self.config.mode_check:
            args.append('--check')

        if self.config.mode_diff:
            args.append('--diff')

        if self.config.limit is not None:
            args.extend(['--limit', self.config.limit])

        if self.config.verbosity is not None:
            args.append(f'-{self.config.verbosity}')

        if self.config.tags is not None:
            args.extend(['--tags', self.config.tags])

        if self.config.skip_tags is not None:
            args.extend(['--skip-tags', self.config.skip_tags])

        return args

    def _generate_args_extra_vars(self) -> list[str]:
        args = []
        if self.config.extra_vars is not None and len(self.config.extra_vars) > 0:
            extra_vars_list = []
            for k in self.config.extra_vars:
                extra_vars_list.append(f"\"{k}\":{json_dumps(self.config.extra_vars[k])}")

            args.extend(
                [
                    '-e',
                    f'{{{",".join(extra_vars_list)}}}'
                ]
            )

        return args

    def generate(self) -> list[str]:
        # see also: official ansible-runner "ansible_runner.RunnerConfig.generate_ansible_command"
        cmd = ['ansible-playbook']

        cmd.extend(self._generate_args_basic())
        cmd.extend(self._generate_args_extra_vars())
        cmd.extend(self._generate_args_auth())

        if self.config.cmd_args is not None:
            cmd.extend(self.config.cmd_args)

        cmd.append(str(self.config.playbook_file))
        return cmd
