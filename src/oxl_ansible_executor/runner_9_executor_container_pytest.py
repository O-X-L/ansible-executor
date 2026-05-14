from pathlib import Path

import pytest

from runner_executor_container import ExecutorContainerDocker, ExecutorContainerPodman, \
    ExecutorContainer
from exceptions import ExecutionError


class DummyContainerExecutor(ExecutorContainer):
    CONTAINER_ENGINE_NAME = 'dummy-engine'

    def _build_container_volumes(self, **kwargs) -> dict:
        return {'/host/path': '/run/ansible'}

    def _build_paths_inside_container(self, **kwargs) -> dict:
        return {'inventory_files': '/run/ansible_inventory'}


@pytest.fixture
def mock_config(mocker):
    config = mocker.MagicMock()
    config.playbook_file = 'test.yml'
    config.playbook_dir = Path('/opt/playbooks')
    config.run_dir = Path('/tmp/run_123')
    config.container_image = 'ansible-executor:latest'
    config.inventory_files = []
    config.ssh_known_hosts_file = None
    config._ssh_key = None
    config.env_vars = None
    config.debug = False
    config.log_stdout_file = None
    config.log_stderr_file = None
    config.container_network = None
    config.container_engine = 'docker'
    config.container_image_pull = False
    config.timeout_container_image_pull_build = 300
    config.timeout_sec_run = 3600
    return config


@pytest.fixture(autouse=True)
def mock_ansible_cmd(mocker):
    # Auto-mock AnsibleCommand globally for these tests so _engine_init doesn't crash 
    # trying to validate missing paths or configurations.
    return mocker.patch('runner_executor_container.AnsibleCommand')


def test_build_container_volumes(mock_config):
    mock_config.inventory_files = [Path('/opt/playbooks/inv'), Path('/etc/ansible/hosts')]
    mock_config.ssh_known_hosts_file = Path('/home/user/.ssh/known_hosts')

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')

    volumes = executor._build_container_volumes(
        pipe_ssh_key=Path('/tmp/ssh_key'),
        pipe_connect_pass=Path('/tmp/conn_pass')
    )

    # Base playbook mapping
    assert volumes[str(mock_config.playbook_dir)] == executor.CONTAINER_PATHS['playbook_dir']

    # Inventory mapping logic actually maps ANY path starting with '/'
    assert volumes['/opt/playbooks/inv'] == f"{executor.CONTAINER_PATHS['inventory_files']}/0"
    assert volumes['/etc/ansible/hosts'] == f"{executor.CONTAINER_PATHS['inventory_files']}/1"

    assert volumes['/tmp/ssh_key'] == executor.CONTAINER_PATHS['pipe_ssh_key']
    assert volumes['/tmp/conn_pass'] == executor.CONTAINER_PATHS['pipe_connect_pass']
    assert volumes['/home/user/.ssh/known_hosts'] == executor.CONTAINER_PATHS['ssh_known_hosts_file']


def test_build_paths_inside_container(mock_config):
    mock_config.inventory_files = [Path('/opt/playbooks/inv'), Path('/etc/ansible/hosts'), Path('relative/inv')]

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor._container_volumes = {
        '/etc/ansible/hosts': '/run/ansible_inventory/1',
        '/opt/playbooks/inv': '/run/ansible_inventory/0'
    }

    paths = executor._build_paths_inside_container(
        pipe_become_pass=Path('/tmp/become_pass')
    )

    # Handled mapping and left unmapped relative path untouched
    assert paths['inventory_files'] == ['/run/ansible_inventory/0', '/run/ansible_inventory/1', Path('relative/inv')]
    assert paths['pipe_become_pass'] == executor.CONTAINER_PATHS['pipe_become_pass']


def test_write_env_var_file(mocker, mock_config):
    mock_write = mocker.patch('runner_executor_container.write_file_with_mode')
    mock_config.env_vars = {'TEST_ENV=': 'val1', 'OTHER': 'val2'}

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor._write_env_var_file()

    mock_write.assert_called_once()
    assert mock_write.call_args[0][0] == Path('/tmp/run_123/.env')
    assert "TEST_ENV=val1\nOTHER=val2" in mock_write.call_args[1]['content']
    assert mock_write.call_args[1]['file_mode'] == 0o600


def test_generate_container_args_network_default(mock_config):
    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    network_args = executor._generate_container_args_network()

    assert isinstance(network_args, list)
    assert '--network=host' in network_args


def test_generate_container_args_network_custom(mock_config):
    mock_config.container_network = 'my-net'
    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    network_args = executor._generate_container_args_network()

    assert '--network' in network_args
    assert 'my-net' in network_args


def test_generate_container_args_volumes(mock_config):
    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor._container_volumes = {
        '/opt/playbooks': '/run/ansible',
        '/etc/ansible/hosts': '/run/ansible_inventory/1'
    }

    vol_args = executor._generate_container_args_volumes()

    assert '-v' in vol_args
    assert '/opt/playbooks:/run/ansible:ro' in vol_args
    assert '/etc/ansible/hosts:/run/ansible_inventory/1:ro' in vol_args


def test_generate_engine_command_docker(mocker, mock_config):
    mocker.patch.object(ExecutorContainerDocker, '_build_engine_executable', return_value='docker')
    mock_config.env_vars = {'A': 'B'}
    mock_config._ssh_key = None

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')

    # Simulate _engine_init pre-computation
    executor._env_var_file = Path('/tmp/run_123/.env')
    executor.ansible_command = ['ansible-playbook', 'test.yml']
    executor._container_volumes = {'/opt/playbooks': '/run/ansible'}
    executor._container_name = 'ansible-executor-123'

    cmd = executor.generate_engine_command()

    assert cmd[0:2] == ['docker', 'run']
    assert '--rm' in cmd
    assert '--name' in cmd and 'ansible-executor-123' in cmd
    assert '-w' in cmd and '/run/ansible' in cmd
    assert '--env-file' in cmd
    assert str(Path('/tmp/run_123/.env')) in cmd
    assert 'ansible-executor:latest' in cmd
    assert 'ansible-playbook' in cmd
    assert 'test.yml' in cmd


def test_generate_engine_command_podman(mocker, mock_config):
    mocker.patch.object(ExecutorContainerPodman, '_build_engine_executable', return_value='podman')
    mock_config.container_engine = 'podman'
    mock_config._ssh_key = None

    executor = ExecutorContainerPodman(config=mock_config, run_id='123')

    # Simulate _engine_init pre-computation
    executor._env_var_file = None
    executor.ansible_command = ['ansible-playbook', 'test.yml']
    executor._container_volumes = {}
    executor._container_name = 'ansible-executor-123'

    cmd = executor.generate_engine_command()

    assert cmd[0:2] == ['podman', 'run']
    assert '--userns=keep-id' in cmd
    assert 'ansible-playbook' in cmd


def test_build_engine_executable_found(mocker, mock_config):
    mock_find_executable = mocker.patch('runner_executor_container.find_executable')
    mock_find_executable.return_value = '/usr/bin/dummy-engine'

    executor = DummyContainerExecutor(config=mock_config, run_id='test1')
    executable = executor._build_engine_executable()

    assert executable == '/usr/bin/dummy-engine'
    mock_find_executable.assert_called_with('dummy-engine')


def test_build_engine_executable_not_found(mocker, mock_config):
    mocker.patch('runner_executor_container.find_executable', return_value=None)

    executor = DummyContainerExecutor(config=mock_config, run_id='test1')
    executable = executor._build_engine_executable()

    assert executable == 'dummy-engine'


def test_engine_init_missing_engine_name(mock_config):
    class InvalidExecutor(ExecutorContainer):
        CONTAINER_ENGINE_NAME = None

    with pytest.raises(NotImplementedError, match='CONTAINER_ENGINE_NAME has to be defined!'):
        InvalidExecutor(config=mock_config, run_id='test1')._engine_init()


def test_engine_init_success(mocker, mock_config, mock_ansible_cmd):
    mocker.patch.object(DummyContainerExecutor, '_build_engine_executable', return_value='dummy-engine')

    mock_cmd_instance = mock_ansible_cmd.return_value
    mock_cmd_instance.generate.return_value = ['ansible-playbook', 'test.yml']

    executor = DummyContainerExecutor(config=mock_config, run_id='test123')
    executor._engine_init()

    assert executor.engine_executable == 'dummy-engine'
    assert executor._container_name == 'ansible-executor-test123'
    assert executor._env_var_file == Path('/tmp/run_123/.env')
    assert executor.ansible_command == ['ansible-playbook', 'test.yml']

    mock_ansible_cmd.assert_called()
    assert mock_ansible_cmd.call_args[1]['config'] == mock_config


def test_prepare_container_image_pull(mocker, mock_config):
    mock_process = mocker.patch('runner_executor_container.process')

    mock_chk = mocker.MagicMock()
    mock_chk.stdout = '1234567890'  # Implies image is found

    mock_pull = mocker.MagicMock()
    mock_pull.failed = False

    mock_process.side_effect = [mock_chk, mock_pull]
    mock_config.container_image_pull = True  # Setup force pull on run

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor.engine_executable = 'docker'
    executor._prepare_container_image()

    assert mock_process.call_count == 2
    assert mock_process.call_args_list[0][1]['cmd'] == [executor.engine_executable, 'images', '-q',
                                                        'ansible-executor:latest']
    assert mock_process.call_args_list[1][1]['cmd'] == [executor.engine_executable, 'image', 'pull',
                                                        'ansible-executor:latest']


def test_prepare_container_image_pull_failure(mocker, mock_config):
    mock_process = mocker.patch('runner_executor_container.process')

    mock_chk = mocker.MagicMock()
    mock_chk.stdout = None  # Image does not exist locally

    mock_pull = mocker.MagicMock()
    mock_pull.failed = True  # Pull fails

    mock_process.side_effect = [mock_chk, mock_pull]

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor.engine_executable = 'docker'

    with pytest.raises(ExecutionError, match="Failed to pull container image"):
        executor._prepare_container_image()


def test_send_signal_to_ansible(mocker, mock_config):
    mock_process = mocker.patch('runner_executor_container.process')

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor.engine_executable = 'docker'
    executor._container_name = 'ansible-executor-123'
    executor._send_signal_to_ansible(15)

    mock_process.assert_called_once()
    cmd = mock_process.call_args[1]['cmd']
    assert cmd == [executor.engine_executable, 'kill', '--signal', '15', executor._container_name]


def test_create_process(mocker, mock_config):
    mock_process_class = mocker.patch('runner_executor_container.Process')

    executor = ExecutorContainerDocker(config=mock_config, run_id='123')
    executor._create_process(['dummy', 'cmd'])

    mock_process_class.assert_called_once()
    assert mock_process_class.call_args[1]['cmd'] == ['dummy', 'cmd']
    assert mock_process_class.call_args[1]['args'].cwd == mock_config.run_dir
