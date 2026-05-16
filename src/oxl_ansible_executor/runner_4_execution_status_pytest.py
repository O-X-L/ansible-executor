import json
import pytest

from runner_execution_status import ExecutionStatus
from runner_config import ExecutionConfig
from utils.subps import ProcessResult
from config import (
    SELECTOR_STATS_LIVE_BEGIN,
    SELECTOR_STATS_RECAP_BEGIN,
    SELECTOR_STATS_RECAP_END,
)


@pytest.fixture
def mock_config(mocker, tmp_path):
    config = mocker.MagicMock(spec=ExecutionConfig)
    config.stats_live = False
    config.stats_recap = False
    config.debug = False

    # Setup dummy log files
    config.log_stdout_file = tmp_path / "stdout.log"
    config.log_stderr_file = tmp_path / "stderr.log"
    config.load_log_stdout = True
    config.load_log_stderr = True

    return config


@pytest.fixture
def mock_executor(mocker):
    executor = mocker.MagicMock()
    executor.time_finish = 12345
    executor.timed_out = False
    executor.signal_stop = False
    executor.ansible_command = ['ansible-playbook', 'site.yml']
    executor.command = ['docker', 'run', 'ansible']

    result = mocker.MagicMock(spec=ProcessResult)
    result.rc = 0
    result.stdout_lines = []

    executor.result = result
    return executor


def test_status_properties(mock_config, mock_executor):
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    assert status.time_finish == 12345
    assert status.timed_out is False
    assert status.canceled is False
    assert status.ansible_command == ['ansible-playbook', 'site.yml']
    assert status.process_command == ['docker', 'run', 'ansible']
    assert status.process_rc == 0
    assert status.finished is True
    assert status.failed is False

    # Test failed state
    mock_executor.result.rc = 1
    assert status.failed is True


def test_get_last_occurrence_in_logs_process_stdout(mock_config, mock_executor):
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    status._cache_process_result = {'stdout_lines': [
        "line 1",
        "PREFIX: found first",
        "line 3",
        "PREFIX: found last",
        "line 5"
    ]}

    res = status._get_last_occurrence_in_logs(10, "PREFIX:")
    assert res == "PREFIX: found last"


def test_get_last_occurrence_in_logs_file_stdout(mock_config, mock_executor):
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor
    mock_executor.result.stdout_lines = []  # Empty so it falls back to parsing log file

    mock_config.log_stdout_file.write_text("line 1\nPREFIX: file matched\nline 3\n")

    res = status._get_last_occurrence_in_logs(10, "PREFIX:")
    assert res == "PREFIX: file matched\n"


def test_playbook_finished(mock_config, mock_executor):
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    # Test success
    status._cache_process_result = {'stdout_lines': ["PLAY RECAP **********", "host1: ok=1"]}
    assert status.playbook_finished is True

    # Test unfound recap
    status._cache_process_result = {'stdout_lines': ["Running task...", "Task success"]}


def test_get_last_stats_valid_json(mock_config, mock_executor):
    mock_config.stats_recap = True
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    stats_dict = {"host1": {"ok": 2, "changed": 1}}
    stats_json_str = f"{SELECTOR_STATS_RECAP_BEGIN}{json.dumps(stats_dict)}{SELECTOR_STATS_RECAP_END}"

    status._cache_process_result = {'stdout_lines': ["log 1", stats_json_str, "log 2"]}

    stats = status.stats
    assert stats == stats_dict

    # Verify the dictionary is properly cached
    assert status._cache_last_stats == stats_dict


def test_get_last_stats_invalid_json(mock_config, mock_executor, mocker):
    mock_config.stats_recap = True
    mock_config.debug = True
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    invalid_json_str = f"{SELECTOR_STATS_RECAP_BEGIN}{{bad_json_payload}}{SELECTOR_STATS_RECAP_END}"
    status._cache_process_result = {'stdout_lines': [invalid_json_str]}

    mock_log = mocker.patch("runner_execution_status.log")

    stats = status.stats

    # Should catch JSONDecodeError, fallback to None, and log exception
    assert stats is None
    mock_log.assert_called_once()
    assert "Failed to parse stats as JSON" in mock_log.call_args[0][0]


def test_stats_by_category(mock_config, mock_executor):
    mock_config.stats_recap = True
    status = ExecutionStatus(mock_config)
    status.executor = mock_executor

    stats_dict = {
        "host1": {"ok": 2, "changed": 1},
        "host2": {"failures": 1}
    }
    status._cache_process_result = {'stdout_lines': [
        f"{SELECTOR_STATS_RECAP_BEGIN}{json.dumps(stats_dict)}{SELECTOR_STATS_RECAP_END}"
    ]}

    cat_stats = status.stats_by_category
    assert cat_stats['ok']['host1'] == 2
    assert cat_stats['changed']['host1'] == 1
    assert cat_stats['failures']['host2'] == 1

    # Missing categories for the host should default to 0
    assert cat_stats['ok'].get('host2', 0) == 0


def test_load_stdout_lines_from_log_file_skip_stats_sections(mock_config):
    mock_config.stats_live = True
    status = ExecutionStatus(mock_config)

    mock_config.log_stdout_file.write_text(
        f"standard log 1\n"
        f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}\n"
        f"standard log 2\n"
    )

    lines = status.stdout_lines
    assert len(lines) == 2
    assert "standard log 1\n" in lines
    assert "standard log 2\n" in lines


def test_load_stdout_lines_from_log_file_after_cleaned(mock_config):
    mock_config.stats_live = True
    status = ExecutionStatus(mock_config)

    # Toggle the cleaned state boolean
    status.set_log_file_cleaned()

    mock_config.log_stdout_file.write_text(
        f"standard log 1\n"
        f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}\n"
        f"standard log 2\n"
    )

    lines = status.stdout_lines
    # Because set_log_file_cleaned() was called, it should bypass skips and return all lines
    assert len(lines) == 3
    assert f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}\n" in lines
