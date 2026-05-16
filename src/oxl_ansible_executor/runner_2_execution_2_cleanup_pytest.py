from pathlib import Path

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests
from runner_execution import ExecutionConfig, Execution, ExecutionStatus
from config import SELECTOR_STATS_RECAP_BEGIN, SELECTOR_STATS_LIVE_BEGIN, SELECTOR_STATS_LIVE_END, \
    SELECTOR_STATS_RECAP_END


@pytest.fixture
def mock_config(mocker, tmp_path: Path):
    config = mocker.MagicMock(spec=ExecutionConfig)

    config.stats_live = True
    config.stats_recap = True
    config.debug = False

    config.log_stdout_file = tmp_path / "ansible_stdout.log"
    config.load_log_stdout = True

    return config


def test_clean_stats_sections_via_status_dynamic_loading(mock_config):
    """Test that ExecutionStatus skips stats payloads when loading standard output lines."""

    original_content = [
        "Normal log line 1\n",
        f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}{SELECTOR_STATS_LIVE_END}\n",
        "Normal log line 2\n",
        f"{SELECTOR_STATS_RECAP_BEGIN}{{recap_stats}}{SELECTOR_STATS_RECAP_END}\n",
        "Normal log line 3\n"
    ]

    with open(mock_config.log_stdout_file, "w", encoding="utf-8") as f:
        f.writelines(original_content)

    status = ExecutionStatus(mock_config)

    # Without log file marked as cleaned, stdout_lines should skip the stats rows natively
    lines = status.stdout_lines
    assert len(lines) == 3
    assert "Normal log line 1\n" in lines
    assert "Normal log line 2\n" in lines
    assert "Normal log line 3\n" in lines


def test_clean_stats_sections_bypass_after_cleaned(mock_config):
    """Test that once set_log_file_cleaned() is called, the raw lines bypass the skip filter."""

    with open(mock_config.log_stdout_file, "w", encoding="utf-8") as f:
        f.writelines([
            "Normal log line 1\n",
            f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}\n",
        ])

    status = ExecutionStatus(mock_config)

    # Flag the file as 'cleaned' meaning we want all remaining raw lines unmodified
    status.set_log_file_cleaned()

    lines = status.stdout_lines
    assert len(lines) == 2
    assert f"{SELECTOR_STATS_LIVE_BEGIN}{{stats}}\n" in lines


def test_execution_status_graceful_missing_file(mock_config, tmp_path: Path):
    """Test that missing log files are handled gracefully without raising exceptions."""

    mock_config.log_stdout_file = tmp_path / "does_not_exist.log"
    status = ExecutionStatus(mock_config)
    assert status.stdout_lines == []


@pytest.mark.parametrize(
    'stats_live, stats_recap, expected_lines',
    [
        (
                True, True,
                ["Normal line 1\n", "Normal line 2\n", "Normal line 3\n"]
        ),
        (
                True, False,
                ["Normal line 1\n", "Normal line 2\n", f"{SELECTOR_STATS_RECAP_BEGIN}payload\n", "Normal line 3\n"]
        ),
        (
                False, True,
                ["Normal line 1\n", f"{SELECTOR_STATS_LIVE_BEGIN}payload\n", "Normal line 2\n", "Normal line 3\n"]
        ),
        (
                False, False,
                ["Normal line 1\n", f"{SELECTOR_STATS_LIVE_BEGIN}payload\n", "Normal line 2\n",
                 f"{SELECTOR_STATS_RECAP_BEGIN}payload\n", "Normal line 3\n"]
        ),
    ]
)
def test_clean_stats_sections_from_stdout_log(tmp_path: Path, stats_live: bool, stats_recap: bool,
                                              expected_lines: list):
    """Test that the master clean method appropriately toggles based on configuration flags."""
    e = Execution(ExecutionConfig(playbook_file='test.yml', playbook_dir=PATH_TEST))

    e.config.stats_live = stats_live
    e.config.stats_recap = stats_recap
    e.config.debug = False  # Ensure coverage over branches

    log_file = tmp_path / "ansible_stdout.log"
    e.config.log_stdout_file = log_file
    e.config.log_file_mode = 0o640

    original_content = [
        "Normal line 1\n",
        f"{SELECTOR_STATS_LIVE_BEGIN}payload\n",
        "Normal line 2\n",
        f"{SELECTOR_STATS_RECAP_BEGIN}payload\n",
        "Normal line 3\n"
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(original_content)

    e._clean_stats_sections_from_stdout_log()

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert lines == expected_lines
