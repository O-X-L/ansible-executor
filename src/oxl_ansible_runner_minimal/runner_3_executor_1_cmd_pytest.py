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
            ['-i', f'{PATH_TEST}/inv1/', '-i', f'{PATH_TEST}/inv2/hosts', f'{PATH_TEST}/test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/',
             'tags': 'config', 'limit': 'srv1,grp2'},
            ['-i', 'inv1/', '--limit', 'srv1,grp2', '--tags', 'config', 'test.yml'],
        ),
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/',
             'tags': ['config', 'service'], 'limit': ['srv1', 'grp2']},
            ['-i', 'inv1/', '--limit', 'srv1,grp2', '--tags', 'config,service', 'test.yml'],
        ),
    ]
)
def test_runner_executor_generate_command(kwargs: dict, args: str):
    from runner_config import ExecutionConfig
    from runner_executor_local import ExecutorLocal

    c = ExecutionConfig(**kwargs)
    e = ExecutorLocal(c)

    cmd = ['ansible-playbook']
    cmd.extend(args)
    assert e.generate_ansible_command() == cmd
