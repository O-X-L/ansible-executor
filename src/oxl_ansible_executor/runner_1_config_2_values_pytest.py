from pathlib import Path
from os import getcwd
from os import remove as remove_file

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests

from config import FALLBACK_CONTAINER_IMAGE


@pytest.fixture(autouse=True)
def run_before_and_after_tests2():
    test_files = {
        f"{getcwd()}/test.yml": b'',
        f"{PATH_TEST}/ssh_key": b'test-sshkey2',
        f"{PATH_TEST}/connect_pass": b'test-connect2',
        f"{PATH_TEST}/become_pass": b'test-become2',
        f"{PATH_TEST}/vault_pass": b'test-vault2',
    }

    for file, content in test_files.items():
        with open(file, 'wb') as f:
            f.write(content)

    yield

    for file in test_files:
        remove_file(file)


@pytest.mark.parametrize(
    'kwargs,expected_values',
    [
        (  # _build_playbook_dir
            {'playbook_file': 'test.yml'},
            {'playbook_dir': Path(getcwd())},
        ),
        (  # _build_list
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'inventory_files': 'inv1/'},
            {'inventory_files': ['inv1/']},
        ),
        (  # _build_list
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'vault_id': 'env1'},
            {'vault_id': ['env1']},
        ),
        (  # _build_csv
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'limit': ['srv1', 'grp2']},
            {'limit': 'srv1,grp2'},
        ),  # _build_csv
        (
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'tags': ['config', 'service1']},
            {'tags': 'config,service1'},
        ),
        (  # _build_csv
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'skip_tags': ['config', 'service1']},
            {'skip_tags': 'config,service1'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_key_value': 'test-sshkey1'},
            {'_ssh_key': 'test-sshkey1'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'ssh_key_file': f"{PATH_TEST}/ssh_key"},
            {'_ssh_key': 'test-sshkey2'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'connect_pass_value': 'test-connect1'},
            {'_connect_pass': 'test-connect1'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'connect_pass_file': f"{PATH_TEST}/connect_pass"},
            {'_connect_pass': 'test-connect2'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'become_pass_value': 'test-become1'},
            {'_become_pass': 'test-become1'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'become_pass_file': f"{PATH_TEST}/become_pass"},
            {'_become_pass': 'test-become2'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'vault_pass_value': 'test-vault1'},
            {'_vault_pass': 'test-vault1'},
        ),
        (  # _build_pass
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'vault_pass_file': f"{PATH_TEST}/vault_pass"},
            {'_vault_pass': 'test-vault2'},
        ),
        (  # _build_container_engine & _build_container_image; todo: will fail if test-env has no docker installed..
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True},
            {'container_engine': 'docker', 'container_image': FALLBACK_CONTAINER_IMAGE},
        ),
        (  # _build_container_image
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'containerized': True,
             'container_image': 'oxlorg/ansible-executor-test'},
            {'container_image': 'oxlorg/ansible-executor-test:latest'},
        ),
        (  # _build_log_file
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'log_stdout_file': '/tmp/ar-stdout.log'},
            {'log_stdout_file': Path('/tmp/ar-stdout.log')},
        ),
        (  # _build_cmd_args
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST,
             'cmd_args': '-f 20 -e some_special_var="hello test"'},
            {'cmd_args': ['-f', '20', '-e', 'some_special_var=hello test']},
        ),
        (  # _validate_verbosity
            {'playbook_file': 'test.yml', 'playbook_dir': PATH_TEST, 'verbosity': 3},
            {'verbosity': 'vvv'},
        ),
    ]
)
def test_runner_config_values(kwargs: dict, expected_values: dict):
    from runner_config import ExecutionConfig

    c = ExecutionConfig(**kwargs)

    for k, v in expected_values.items():
        assert hasattr(c, k)
        assert getattr(c, k) == v
