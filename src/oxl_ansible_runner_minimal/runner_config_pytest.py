from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

import pytest

PATH_TEST = Path(mkdtemp(prefix='ar_test'))


@pytest.fixture(autouse=True)
def run_before_and_after_tests(tmpdir):
    PATH_TEST.mkdir(exist_ok=True)
    with open(f'{PATH_TEST}/test.yml', 'wb') as f:
        f.write(b'')

    with open(f'{PATH_TEST}/test.yml', 'wb') as f:
        f.write(b'')

    (PATH_TEST / 'inv1').mkdir(exist_ok=True)
    (PATH_TEST / 'inv2').mkdir(exist_ok=True)
    with open(f'{PATH_TEST}/inv2/hosts', 'wb') as f:
        f.write(b'')

    yield

    rmtree(PATH_TEST)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': 'abc.yml'}),
        ({'playbook_file': 'test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': '/tmp/abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv/hosts.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'extra_vars': 'nope=me'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars': 'nope=me'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_run': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 12.2}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_key_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'connect_pass_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'become_pass_file': '/tmp/does-not-exist'}),
    ]
)
def test_runner_config_validation_failures(kwargs: dict):
    from runner import Config, ConfigError

    with pytest.raises(ConfigError):
        Config(**kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv2/hosts'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': ['inv1/', 'inv2/hosts']}),
    ]
)
def test_runner_config_validation_success(kwargs: dict):
    from runner import Config

    Config(**kwargs)


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
def test_runner_config_generate_command(kwargs: dict, args: str):
    from runner import Config

    c = Config(**kwargs)
    cmd = ['ansible-playbook']
    cmd.extend(args)
    assert c.generate_ansible_command() == cmd


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stdout_file': f'{PATH_TEST}/test_stdout.log'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stderr_file': f'{PATH_TEST}/test_stderr.log'}),
    ]
)
def test_runner_config_ensure_log_files(kwargs: dict):
    from runner import Config

    c = Config(**kwargs)

    assert c.log_stdout_file is not None
    assert c.log_stderr_file is not None

    assert c.log_stdout_file.is_file()
    assert c.log_stderr_file.is_file()
