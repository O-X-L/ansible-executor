from pathlib import Path

import pytest

from runner_0_base_pytest import PATH_TEST, run_before_and_after_tests
from runner_execution import ExecutionConfig, Execution
from config import SELECTOR_STATS_RECAP_BEGIN, SELECTOR_STATS_LIVE_BEGIN, SELECTOR_STATS_LIVE_END, \
    SELECTOR_STATS_RECAP_END


def test_clean_stats_sections_from_stdout_log_single(tmp_path: Path):
    """Test cleaning a specific selector from the log file natively."""
    e = Execution(ExecutionConfig(playbook_file='test.yml', playbook_dir=PATH_TEST))

    log_file = tmp_path / "ansible_stdout.log"
    e.config.log_stdout_file = log_file
    e.config.log_file_mode = 0o640

    original_content = [
        "Normal log line 1\n",
        f"{SELECTOR_STATS_LIVE_BEGIN}some_live_payload{SELECTOR_STATS_LIVE_END}\n",
        "Normal log line 2\n",
        f"{SELECTOR_STATS_RECAP_BEGIN}some_recap_payload{SELECTOR_STATS_RECAP_END}\n",
        "Normal log line 3\n"
    ]

    with open(log_file, "w", encoding="utf-8") as f:
        f.writelines(original_content)

    e._clean_stats_sections_from_stdout_log_single(SELECTOR_STATS_LIVE_BEGIN)

    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 4
    assert lines[0] == "Normal log line 1\n"
    assert lines[1] == "Normal log line 2\n"
    assert lines[2] == f"{SELECTOR_STATS_RECAP_BEGIN}some_recap_payload{SELECTOR_STATS_RECAP_END}\n"
    assert lines[3] == "Normal log line 3\n"


def test_clean_stats_sections_from_stdout_log_single_file_not_found(tmp_path: Path):
    """Test that missing log files are handled gracefully without raising exceptions."""
    e = Execution(ExecutionConfig(playbook_file='test.yml', playbook_dir=PATH_TEST))

    log_file = tmp_path / "does_not_exist.log"
    e.config.log_stdout_file = log_file
    e.config.log_file_mode = 0o640

    e._clean_stats_sections_from_stdout_log_single(SELECTOR_STATS_LIVE_BEGIN)

    assert not log_file.exists()


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
