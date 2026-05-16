from pathlib import Path

import pytest

from oxl_ansible_executor.runner_executor_local import ExecutorLocal
from oxl_ansible_executor.config import ENV_ANSIBLE_CALLBACK_PLUGINS


@pytest.fixture
def mock_config(mocker):
    config = mocker.MagicMock()
    config.playbook_dir = Path('/opt/playbooks')
    config.inventory_files = ['/opt/playbooks/inventory.yml']
    config.ssh_known_hosts_file = Path('/home/user/.ssh/known_hosts')
    config._ssh_key = None
    config.timeout_sec_run = 3600
    config.env_vars = {'TEST_VAR': '123'}
    config.env_vars_strip = ['UNWANTED_VAR']
    config.log_stdout_file = Path('/tmp/stdout.log')
    config.log_stderr_file = Path('/tmp/stderr.log')
    return config


@pytest.fixture(autouse=True)
def mock_ansible_cmd(mocker):
    # Auto-mock AnsibleCommand globally so instantiating ExecutorLocal doesn't execute real command generation
    return mocker.patch('oxl_ansible_executor.runner_executor_local.AnsibleCommand')


def test_build_engine_executable_found(mocker):
    mock_find_executable = mocker.patch('oxl_ansible_executor.runner_executor_local.find_executable')
    mock_find_executable.return_value = '/usr/local/bin/ansible-playbook'

    executable = ExecutorLocal._build_engine_executable()

    assert executable == '/usr/local/bin/ansible-playbook'
    mock_find_executable.assert_called_once_with('ansible-playbook')


def test_build_engine_executable_not_found(mocker):
    mocker.patch('oxl_ansible_executor.runner_executor_local.find_executable', return_value=None)

    executable = ExecutorLocal._build_engine_executable()

    assert executable == 'ansible-playbook'


def test_engine_init(mocker, mock_config, mock_ansible_cmd):
    mocker.patch.object(ExecutorLocal, '_build_engine_executable', return_value='/bin/ansible-playbook')

    mock_ansible_cmd_instance = mock_ansible_cmd.return_value
    mock_ansible_cmd_instance.generate.return_value = ['ansible-playbook', 'site.yml']

    pipe_ssh = Path('/tmp/pipe_ssh')
    pipe_conn = Path('/tmp/pipe_conn')
    pipe_become = Path('/tmp/pipe_become')
    pipe_vault = Path('/tmp/pipe_vault')

    # Instantiating ExecutorLocal calls _engine_init internally via ExecutorBase.__init__
    executor = ExecutorLocal(
        config=mock_config,
        run_id='123',
        pipe_ssh_key=pipe_ssh,
        pipe_connect_pass=pipe_conn,
        pipe_become_pass=pipe_become,
        pipe_vault_pass=pipe_vault
    )

    assert executor.engine_executable == '/bin/ansible-playbook'
    assert executor.ansible_command == ['ansible-playbook', 'site.yml']

    mock_ansible_cmd.assert_called_once_with(
        config=mock_config,
        pipe_connect_pass=pipe_conn,
        pipe_become_pass=pipe_become,
        pipe_vault_pass=pipe_vault,
        inventory_files=mock_config.inventory_files,
        ssh_known_hosts_file=mock_config.ssh_known_hosts_file,
    )


def test_generate_engine_command_without_ssh_key(mock_config):
    executor = ExecutorLocal(config=mock_config, run_id='123')
    executor.engine_executable = '/opt/bin/ansible-playbook'
    executor.ansible_command = ['ansible-playbook', '-i', 'inv', 'playbook.yml']

    cmd = executor.generate_engine_command()

    # The first element should be replaced by the discovered engine_executable
    assert cmd == ['/opt/bin/ansible-playbook', '-i', 'inv', 'playbook.yml']


def test_generate_engine_command_with_ssh_key(mocker, mock_config):
    mock_config._ssh_key = 'some-key-content'
    mock_wrap = mocker.patch('oxl_ansible_executor.runner_executor_local.wrap_cmd_in_ssh_agent')
    mock_wrap.return_value = ['ssh-agent', 'bash', '-c', 'ansible-playbook playbook.yml']

    executor = ExecutorLocal(config=mock_config, run_id='123')
    executor.engine_executable = '/opt/bin/ansible-playbook'
    executor.ansible_command = ['ansible-playbook', 'playbook.yml']
    executor._pipe_ssh_key = Path('/tmp/run_123/ssh_key')

    cmd = executor.generate_engine_command()

    assert cmd == ['ssh-agent', 'bash', '-c', 'ansible-playbook playbook.yml']
    mock_wrap.assert_called_once_with(
        cmd=['/opt/bin/ansible-playbook', 'playbook.yml'],
        ssh_key_file=Path('/tmp/run_123/ssh_key')
    )


def test_prepare_engine(mock_config):
    executor = ExecutorLocal(config=mock_config, run_id='123')
    # Method does nothing, just ensure it doesn't raise an exception
    executor._prepare_engine()


def test_create_process(mocker, mock_config):
    mock_process_class = mocker.patch('oxl_ansible_executor.runner_executor_local.Process')
    mock_process_args_class = mocker.patch('oxl_ansible_executor.runner_executor_local.ProcessArgs')

    mock_process_args_instance = mocker.MagicMock()
    mock_process_args_class.return_value = mock_process_args_instance

    executor = ExecutorLocal(config=mock_config, run_id='123')
    cmd = ['ansible-playbook', 'test.yml']

    executor._create_process(cmd)

    mock_process_args_class.assert_called_once_with(
        cwd=mock_config.playbook_dir,
        timeout_sec=mock_config.timeout_sec_run,
        env=mock_config.env_vars,
        env_inherit=True,
        env_remove=mock_config.env_vars_strip,
        file_stdout=mock_config.log_stdout_file,
        file_stderr=mock_config.log_stderr_file,
    )

    mock_process_class.assert_called_once_with(
        cmd=cmd,
        args=mock_process_args_instance
    )
    assert executor.process == mock_process_class.return_value


def test_send_signal_to_ansible(mocker, mock_config):
    executor = ExecutorLocal(config=mock_config, run_id='123')
    executor.process = mocker.MagicMock()

    executor._send_signal_to_ansible(15)

    executor.process.send_signal.assert_called_once_with(15)


def test_add_stats_plugins_path_import_error(mocker, mock_config):
    # Simulate missing oxl_ansible_executor_plugins module
    mocker.patch.dict('sys.modules', {'oxl_ansible_executor_plugins': None})

    executor = ExecutorLocal(config=mock_config, run_id='123')
    executor.config.env_vars = {}

    executor._add_stats_plugins_path()

    # Ensuring add_to_dict was aborted/never called
    executor.config.add_to_dict.assert_not_called()


def test_add_stats_plugins_path_empty_env(mocker, mock_config):
    # Mock the plugin module and its method
    mock_plugins_module = mocker.MagicMock()
    mock_plugins_module.get_path_callback.return_value = '/custom/stats/path'
    mocker.patch.dict('sys.modules', {'oxl_ansible_executor_plugins': mock_plugins_module})

    executor = ExecutorLocal(config=mock_config, run_id='123')
    executor.config.env_vars = {}

    executor._add_stats_plugins_path()

    # Check that add_to_dict was called with the correct parameters
    executor.config.add_to_dict.assert_called_once_with(
        {},
        key=ENV_ANSIBLE_CALLBACK_PLUGINS,
        value='/custom/stats/path'
    )


def test_add_stats_plugins_path_existing_env(mocker, mock_config):
    mock_plugins_module = mocker.MagicMock()
    mock_plugins_module.get_path_callback.return_value = '/custom/stats/path'
    mocker.patch.dict('sys.modules', {'oxl_ansible_executor_plugins': mock_plugins_module})

    executor = ExecutorLocal(config=mock_config, run_id='123')
    existing_env = {ENV_ANSIBLE_CALLBACK_PLUGINS: '/existing/path'}
    executor.config.env_vars = existing_env.copy()

    executor._add_stats_plugins_path()

    # Path should be appended using a colon
    executor.config.add_to_dict.assert_called_once_with(
        existing_env,
        key=ENV_ANSIBLE_CALLBACK_PLUGINS,
        value='/existing/path:/custom/stats/path'
    )


def test_add_stats_plugins_path_idempotent(mocker, mock_config):
    mock_plugins_module = mocker.MagicMock()
    mock_plugins_module.get_path_callback.return_value = '/custom/stats/path'
    mocker.patch.dict('sys.modules', {'oxl_ansible_executor_plugins': mock_plugins_module})

    executor = ExecutorLocal(config=mock_config, run_id='123')
    existing_env = {ENV_ANSIBLE_CALLBACK_PLUGINS: '/other/path:/custom/stats/path'}
    executor.config.env_vars = existing_env.copy()

    executor._add_stats_plugins_path()

    # It shouldn't duplicate the injected path if it already exists
    executor.config.add_to_dict.assert_called_once_with(
        existing_env,
        key=ENV_ANSIBLE_CALLBACK_PLUGINS,
        value='/other/path:/custom/stats/path'
    )
