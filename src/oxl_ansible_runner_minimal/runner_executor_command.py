from pathlib import Path
from json import dumps as json_dumps

from runner_config import ExecutionConfig


def generate_ansible_command(config: ExecutionConfig, secret_args: list[str]) -> list[str]:
    # cleaned-up & simplified version of the official "ansible_runner.RunnerConfig.generate_ansible_command"
    # pylint: disable=R0912
    cmd = ['ansible-playbook']

    if config.inventory_files is not None:
        for i in config.inventory_files:
            cmd.extend(['-i', str(i)])

    if config.mode_check:
        cmd.append('--check')

    if config.mode_diff:
        cmd.append('--diff')

    if config.limit is not None:
        cmd.extend(['--limit', config.limit])

    if config.extra_vars is not None and len(config.extra_vars) > 0:
        extra_vars_list = []
        for k in config.extra_vars:
            extra_vars_list.append(f"\"{k}\":{json_dumps(config.extra_vars[k])}")

        cmd.extend(
            [
                '-e',
                f'{{{",".join(extra_vars_list)}}}'
            ]
        )

    if config.verbosity is not None:
        cmd.append(f'-{config.verbosity}')

    if config.tags is not None:
        cmd.extend(['--tags', config.tags])

    if config.skip_tags is not None:
        cmd.extend(['--skip-tags', config.skip_tags])

    if config.ssh_known_hosts_file is not None:
        cmd.extend([
            '-e',
            f"ansible_ssh_extra_args='-o UserKnownHostsFile={config.ssh_known_hosts_file}'",
        ])

    if config.connect_user is not None:
        cmd.extend(['--user', config.connect_user])

    if config.become_user is not None:
        cmd.extend(['--become-user', config.become_user])

    if config.vault_id is not None:
        for vault_id in config.vault_id:
            cmd.extend(['--vault-id', vault_id])

    cmd.extend(secret_args)

    if config.cmd_args is not None:
        cmd.extend(config.cmd_args)

    cmd.append(str(config.playbook_file))
    return cmd


def generate_secret_cmd_args(
        config: ExecutionConfig,
        pipe_ssh_key: (Path, None),
        pipe_connect_pass: (Path, None),
        pipe_become_pass: (Path, None),
        pipe_vault_pass: (Path, None),
) -> list[str]:
    # pylint: disable=W0212
    args = []
    if config._ssh_key is not None and pipe_ssh_key is not None:
        args.extend(['--private-key', str(pipe_ssh_key)])

    if config._connect_pass is not None and pipe_connect_pass is not None:
        args.extend(['--connection-password-file', str(pipe_connect_pass)])

    if config._become_pass is not None and pipe_become_pass is not None:
        args.extend(['--become-password-file', str(pipe_become_pass)])

    if config._vault_pass is not None and pipe_vault_pass is not None:
        args.extend(['--vault-password-file', str(pipe_vault_pass)])

    return args
