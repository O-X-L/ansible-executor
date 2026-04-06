from pathlib import Path
from tempfile import mktemp

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': 'abc.yml'}),
        ({'playbook_file': 'test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'does-not-exist/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/does-not-exist.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'run_dir': '/tmp/does-not-exist/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_known_hosts_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_known_hosts_file': 'does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': -1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 8}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_check': 'no'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_check': 0}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_diff': 'no'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_diff': 0}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': 'yes'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': 1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'extra_vars': 'nope=me'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'extra_vars': ['test', 'abc']}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars': 'nope=me'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars': ['test', 'abc']}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars_strip': 'nope=me'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_run': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 'abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 12.2}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 5}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': 'nope'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': 'rwxrwxrwx'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': 640}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': 3}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': False}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_owner_group': -1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_owner_group': 'does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'cmd_args': -1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'cmd_args': {'abc': 'no'}}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_key_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'connect_pass_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'become_pass_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'vault_pass_file': '/tmp/does-not-exist'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True, 'container_engine': 'nope'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True, 'container_engine': 'dummy'}),
    ]
)
def test_runner_config_validation_failures(kwargs: dict, mocker):
    mocker.patch('config.CONTAINER_ENGINES', return_value=('docker', 'podman', 'dummy'))

    from runner_config import ExecutionConfig, ConfigError

    with pytest.raises(ConfigError):
        ExecutionConfig(**kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 'v'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_check': True}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'mode_diff': True}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv2/hosts'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': ['inv1/', 'inv2/hosts']}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'extra_vars': {'abc': 'yes'}}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars': {'ANSIBLE_WHATEVER': '1'}}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'env_vars_strip': ['SECRET']}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_run': 7200}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'timeout_sec_start': 60}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_mode': 0o644}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_owner_group': 'adm'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_file_owner_group': 1000}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'cmd_args': ['-f', '20']}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True, 'container_engine': 'podman'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True, 'container_engine': 'docker'}),
    ]
)
def test_runner_config_validation_success(kwargs: dict):
    from runner_config import ExecutionConfig

    ExecutionConfig(**kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stdout_file': f'{PATH_TEST}/test_stdout.log'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stderr_file': f'{PATH_TEST}/test_stderr.log'}),
    ]
)
def test_runner_config_ensure_log_files(kwargs: dict):
    from runner_config import ExecutionConfig

    c = ExecutionConfig(**kwargs)

    if c.log_stdout_file is not None:
        assert isinstance(c.log_stdout_file, Path)

    if c.log_stderr_file is not None:
        assert isinstance(c.log_stderr_file, Path)


@pytest.mark.parametrize(
    'which_log',
    [
        'stdout',
        'stderr',
    ]
)

def test_runner_config_validation_failure_log_file_exists(which_log: str):
    log_file = mktemp(prefix='ar_test')
    with open(log_file, 'wb') as f:
        f.write(b'')

    from runner_config import ExecutionConfig, ConfigError

    with pytest.raises(ConfigError):
        ExecutionConfig(
            **{'playbook_file': f'{PATH_TEST}/test.yml', f'log_{which_log}_file': log_file}
        )
