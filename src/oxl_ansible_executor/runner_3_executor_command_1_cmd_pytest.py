from pathlib import Path

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests


@pytest.mark.parametrize(
    'kwargs,args',
    [
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST},
            ['test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/'},
            ['-i', 'inv1/', 'test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv2/hosts'},
            ['-i', 'inv2/hosts', 'test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': ['inv1/', 'inv2/hosts']},
            ['-i', 'inv1/', '-i', 'inv2/hosts', 'test.yml'],
        ),
        (
            {'playbook_file': f'{PATH_TEST}/test.yml',
             'inventory_files': [f'{PATH_TEST}/inv1/', f'{PATH_TEST}/inv2/hosts']},
            ['-i', 'inv1', '-i', 'inv2/hosts', 'test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/',
             'tags': 'config', 'limit': 'srv1,grp2'},
            ['-i', 'inv1/', '-l', 'srv1,grp2', '-t', 'config', 'test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/',
             'tags': ['config', 'service'], 'limit': ['srv1', 'grp2']},
            ['-i', 'inv1/', '-l', 'srv1,grp2', '-t', 'config,service', 'test.yml'],
        ),
    ]
)
def test_runner_executor_generate_command_wo_secrets(kwargs: dict, args: str):
    from runner_config import ExecutionConfig
    from runner_executor_command import AnsibleCommand

    c = ExecutionConfig(**kwargs)
    a = AnsibleCommand(
        config=c,
        pipe_connect_pass=None,
        pipe_become_pass=None,
        pipe_vault_pass=None,
        inventory_files=c.inventory_files,
        ssh_known_hosts_file=c.ssh_known_hosts_file,
    )

    assert a.generate()[1:] == args


def test_runner_executor_generate_command_ssh_agent():
    from runner_executor_command import wrap_cmd_in_ssh_agent

    assert wrap_cmd_in_ssh_agent(
        cmd=['ansible-playbook', '-i', 'inv/test/hosts', '-l', 'srv1,grp2', '-e', '{"test":"test5"}', 'play1.yml'],
        ssh_key_file=Path('/tmp/dummy'),
    ) == [
        'ssh-agent',
        'sh', '-c',
        'ssh-add /tmp/dummy && ansible-playbook -i inv/test/hosts -l srv1,grp2 -e \'{"test":"test5"}\' play1.yml',
    ]


@pytest.mark.parametrize(
    'kwargs,args',
    [
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST},
            ['test.yml'],
        ),
    ]
)
def test_runner_executor_generate_command_with_secrets(kwargs: dict, args: str):
    from runner_config import ExecutionConfig
    from runner_executor_command import AnsibleCommand

    c = ExecutionConfig(**kwargs)
    a = AnsibleCommand(
        config=c,
        pipe_connect_pass=None,
        pipe_become_pass=None,
        pipe_vault_pass=None,
        inventory_files=c.inventory_files,
        ssh_known_hosts_file=c.ssh_known_hosts_file,
    )

    assert a.generate()[1:] == args