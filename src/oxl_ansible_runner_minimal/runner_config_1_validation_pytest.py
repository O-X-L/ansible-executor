from pathlib import Path

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests



@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': 'abc.yml'}),
        ({'playbook_file': 'test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': '/tmp/abc'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv/hosts.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 'abc'}),
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
    from runner_config import Config, ConfigError

    with pytest.raises(ConfigError):
        Config(**kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 1}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 'v'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv2/hosts'}),
        ({'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': ['inv1/', 'inv2/hosts']}),
    ]
)
def test_runner_config_validation_success(kwargs: dict):
    from runner_config import Config

    Config(**kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        ({'playbook_file': f'{PATH_TEST}/test.yml'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stdout_file': f'{PATH_TEST}/test_stdout.log'}),
        ({'playbook_file': f'{PATH_TEST}/test.yml', 'log_stderr_file': f'{PATH_TEST}/test_stderr.log'}),
    ]
)
def test_runner_config_ensure_log_files(kwargs: dict):
    from runner_config import Config

    c = Config(**kwargs)

    if c.log_stdout_file is not None:
        assert isinstance(c.log_stdout_file, Path)

    if c.log_stderr_file is not None:
        assert isinstance(c.log_stderr_file, Path)
