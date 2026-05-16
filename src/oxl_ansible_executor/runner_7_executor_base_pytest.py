import pytest

from runner_executor_base import ExecutorBase
from runner_config import ExecutionConfig
from config import CALLBACK_PLUGIN_STATS_LIVE, CALLBACK_PLUGIN_STATS_RECAP


class DummyExecutor(ExecutorBase):
    def _engine_init(self, **kwargs):
        pass

    def _prepare_engine(self):
        pass

    def _create_process(self, cmd):
        pass

    def _send_signal_to_ansible(self, signum):
        self.mock_sent_signals.append(signum)

    def generate_engine_command(self) -> list:
        return ['dummy', 'command']


@pytest.fixture
def mock_config(mocker):
    config = mocker.MagicMock(spec=ExecutionConfig)
    config.timeout_sec_run = 300  # 5 minute timeout

    # Explicitly set these so the base executor doesn't crash or behave weirdly
    config.debug = False
    config.env_vars = {}
    config.output_color = False
    config.stats_live = False
    config.stats_recap = True

    def mock_add_to_dict(d: dict, key: str, value: str):
        d[key] = value
        return d

    config.add_to_dict.side_effect = mock_add_to_dict

    return config


@pytest.fixture
def executor(mock_config, mocker):
    exec_inst = DummyExecutor(config=mock_config, run_id='test-123')
    exec_inst.mock_sent_signals = []

    # Mock the internal process object and its result
    exec_inst.process = mocker.MagicMock()
    exec_inst.process.is_alive.return_value = True

    # Important: The control loop expects rc to be -1 while running
    class FakeResult:
        rc = -1

    exec_inst.process.result = FakeResult()

    return exec_inst


def test_prepare_base(mock_config):
    executor = DummyExecutor(config=mock_config, run_id='123')
    mock_config.output_color = True

    # If your base uses an internal mechanism to add to env_vars, this mock allows it
    mock_config.add_to_dict.return_value = {'ANSIBLE_FORCE_COLOR': '1'}

    executor._prepare_base()

    # Just asserting it doesn't crash. If you have specific env_var logic, it runs here.
    assert isinstance(executor.config.env_vars, dict)


def test_wait_for_process_to_finish(executor):
    executor.process.result.rc = 0
    executor._wait_for_process_to_finish()

    executor.process.wait_until_finished.assert_called_once()
    executor.process.close.assert_called_once()

    assert executor.result.rc == 0
    assert getattr(executor, 'time_finish', 0) != -1


def test_process_control_loop_graceful_exit(mocker, executor):
    mocker.patch('runner_executor_base.time', return_value=100)  # freeze time so it never times out

    state = {'calls': 0}

    def sleep_side_effect(sec):
        state['calls'] += 1
        if state['calls'] >= 2:
            # Simulate the process finishing on its own during the sleep
            executor.process.result.rc = 0
            executor.process.is_alive.return_value = False

    mock_sleep = mocker.patch('runner_executor_base.sleep', side_effect=sleep_side_effect)

    executor._process_control_loop()

    # Loop exited successfully without hitting timeouts
    assert mock_sleep.call_count == 2
    assert not executor.timed_out
    assert len(executor.mock_sent_signals) == 0


def test_process_control_loop_timeout_triggered(mocker, executor):
    start_time = 1000
    timeout = executor.config.timeout_sec_run  # 300

    time_returns = [
        start_time,  # initial start time
        start_time + 10,  # loop 1: within limits
        start_time + timeout + 1,  # loop 2: exceeds timeout!
        start_time + timeout + 5,  # looping while waiting for kill
        start_time + timeout + 15,  # looping while escalating
    ]

    def time_side_effect():
        if time_returns:
            return time_returns.pop(0)
        return start_time + timeout + 30

    mocker.patch('runner_executor_base.time', side_effect=time_side_effect)

    # Failsafe sleep to prevent the infinite loop and simulate the kill taking effect
    state = {'calls': 0}

    def sleep_side_effect(sec):
        state['calls'] += 1
        # Once the timeout sets signal_stop, we let it loop a couple of times to send
        # the escalation signals, then we simulate the process dying.
        if getattr(executor, 'signal_stop', False) and state['calls'] > 3:
            executor.process.result.rc = -9
            executor.process.is_alive.return_value = False

        # Absolute failsafe
        if state['calls'] > 10:
            executor.process.result.rc = -9
            executor.process.is_alive.return_value = False

    mocker.patch('runner_executor_base.sleep', side_effect=sleep_side_effect)

    executor._process_control_loop()

    assert executor.timed_out is True
    assert executor.signal_stop is True

    # Should have sent SIGINT (2) then SIGKILL (9) to Ansible due to timeout escalation
    assert executor.mock_sent_signals == [2, 9]

    # And fallback SIGTERM (15) and SIGKILL (9) to the Process Object itself
    assert executor.process.send_signal.call_count >= 1


def test_process_control_loop_external_signal_stop(mocker, executor):
    mocker.patch('runner_executor_base.time', return_value=1000)

    # Simulate an external thread setting signal_stop = True before the loop
    executor.signal_stop = True

    state = {'calls': 0}

    def sleep_side_effect(sec):
        state['calls'] += 1
        # Process dies shortly after receiving the stop signal
        if state['calls'] >= 2:
            executor.process.result.rc = -15
            executor.process.is_alive.return_value = False

    mocker.patch('runner_executor_base.sleep', side_effect=sleep_side_effect)

    executor._process_control_loop()

    # Even though we didn't time out, signal_stop was True, so it should send termination signals
    assert executor.timed_out is False
    assert executor.mock_sent_signals == [2, 9]


@pytest.mark.parametrize(
    'initial_callbacks, stats_live, stats_recap, expected_callbacks',
    [
        # 1. No existing callbacks in env_vars
        (None, False, True, [CALLBACK_PLUGIN_STATS_RECAP]),
        (None, True, False, [CALLBACK_PLUGIN_STATS_LIVE]),
        (None, True, True, [CALLBACK_PLUGIN_STATS_RECAP, CALLBACK_PLUGIN_STATS_LIVE]),
        (None, False, False, []),

        # 2. Existing callbacks in env_vars (single)
        ('profile_tasks', False, True, ['profile_tasks', CALLBACK_PLUGIN_STATS_RECAP]),
        ('profile_tasks', True, False, ['profile_tasks', CALLBACK_PLUGIN_STATS_LIVE]),
        ('profile_tasks', True, True, ['profile_tasks', CALLBACK_PLUGIN_STATS_RECAP, CALLBACK_PLUGIN_STATS_LIVE]),

        # 3. Existing callbacks in env_vars (multiple)
        ('profile_tasks,timer', True, True,
         ['profile_tasks', 'timer', CALLBACK_PLUGIN_STATS_RECAP, CALLBACK_PLUGIN_STATS_LIVE]),
    ]
)
def test_enable_stats_plugins(executor, initial_callbacks, stats_live, stats_recap, expected_callbacks):
    """Test that ansible callback plugins are accurately appended to the environment variables."""

    if initial_callbacks is not None:
        executor.config.env_vars['ANSIBLE_CALLBACKS_ENABLED'] = initial_callbacks

    executor.config.stats_live = stats_live
    executor.config.stats_recap = stats_recap

    # Run the method
    executor._enable_stats_plugins()

    # Validate the environment variables were updated correctly
    actual_callbacks = executor.config.env_vars.get('ANSIBLE_CALLBACKS_ENABLED', '')

    if not expected_callbacks:
        assert actual_callbacks == ''
    else:
        assert actual_callbacks == ','.join(expected_callbacks)

    # Ensure config.add_to_dict was actually called to perform the assignment
    executor.config.add_to_dict.assert_called_once()
