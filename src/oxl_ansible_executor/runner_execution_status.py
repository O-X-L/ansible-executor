from time import time
from pathlib import Path
from collections import deque
from typing import Dict, TypedDict
from json import loads as json_loads
from json import dumps as json_dumps, JSONDecodeError

from utils.debug import log
from runner_config import ExecutionConfig
from runner_executor_local import ExecutorBase
from config import SELECTOR_STATS_LIVE_BEGIN, SELECTOR_STATS_RECAP_BEGIN, SELECTOR_STATS_RECAP_END, \
    SELECTOR_STATS_LIVE_END


class AnsiblePlaybookHostStats(TypedDict):
    ok: int
    changed: int
    unreachable: int
    failures: int
    skipped: int
    rescued: int
    ignored: int

AnsiblePlaybookStatsByHost = Dict[str, AnsiblePlaybookHostStats]

ANSIBLE_STATS_CATEGORIES = ['ok', 'changed', 'unreachable', 'failures', 'skipped', 'rescued', 'ignored']
class AnsiblePlaybookStatsByCategory(TypedDict):
    ok: dict[str, int]
    changed: dict[str, int]
    unreachable: dict[str, int]
    failures: dict[str, int]
    skipped: dict[str, int]
    rescued: dict[str, int]
    ignored: dict[str, int]


# pylint: disable=R0904
class ExecutionStatus:
    def __init__(self, config: ExecutionConfig):
        self._config: ExecutionConfig = config
        self.time_start = int(time())
        self._executor: (None, ExecutorBase) = None
        self._cache_process_result: (None, dict) = None
        self._cache_stdout_lines: (None, list[str]) = None
        self._cache_stderr_lines: (None, list[str]) = None
        self._cache_last_stats: (None, dict) = None
        self._log_stdout_stats_cleaned: bool = False

    # todo: use properties to add executor-infos to execution-status
    @property
    def executor(self) -> None:
        return None

    @executor.setter
    def executor(self, executor: ExecutorBase):
        self._executor = executor

    @property
    def time_finish(self) -> int:
        return self._executor.time_finish

    @property
    def timed_out(self) -> bool:
        return self._executor.timed_out

    @property
    def canceled(self) -> bool:
        return self._executor.signal_stop

    @property
    def ansible_command(self) -> (None, list[str]):
        if self._executor is None:
            return None

        return self._executor.ansible_command

    @property
    def process_command(self) -> (None, list[str]):
        if self._executor is None:
            return None

        return self._executor.command

    @property
    def process_rc(self) -> int:
        if self._executor is None or self._executor.result is None:
            return -1

        return self._executor.result.rc

    @property
    def process_result(self) -> (dict, None):
        if self._executor is None or self._executor.result is None:
            return None

        if self._cache_process_result is not None:
            return self._cache_process_result

        result = self._executor.result.to_dict()
        result['stdout_lines'] = self.stdout_lines
        result['stdout'] = self.stdout
        result['stderr_lines'] = self.stderr_lines
        result['stderr'] = self.stderr

        if self.finished:
            self._cache_process_result = result

        return result

    @property
    def finished(self) -> bool:
        return self.process_rc != -1

    @property
    def failed(self) -> bool:
        if not self.finished:
            return False

        if self.process_result is None:
            # bug? should not happen
            return True

        return self.process_rc != 0

    def _get_last_occurrence_in_logs(self, tail_line_count: int, line_start: str) -> (None, str):
        have_process_stdout = self._executor.result is not None and len(self._executor.result.stdout_lines) > 0
        have_log_file_stdout = self._config.log_stdout_file is not None

        if not have_process_stdout and not have_log_file_stdout:
            # no data to work with
            return None

        lines_to_search = []
        if have_process_stdout:
            lines_to_search = deque(self._executor.result.stdout_lines, maxlen=tail_line_count)

        else:
            with open(self._config.log_stdout_file, 'r', encoding='utf-8') as file:
                lines_to_search = deque(file, maxlen=tail_line_count)

        lines_to_search.reverse()
        for line in lines_to_search:
            if line.startswith(line_start):
                return line

        return None

    @property
    def playbook_finished(self) -> bool:
        # true if:
        #   ansible-process finished
        #   neither process-stdout nor log-file are available (no data to work with)
        #   either process-stdout or log-file have a 'PLAY RECAP'-line

        if not self.finished or self.process_result is None:
            return False

        play_recap = self._get_last_occurrence_in_logs(tail_line_count=100, line_start='PLAY RECAP')
        if play_recap is None:
            return False

        return True

    @staticmethod
    def _build_valid_stats(unverified_stats: dict) -> AnsiblePlaybookStatsByHost:
        valid_stats = {}
        if not isinstance(unverified_stats, dict):
            return valid_stats

        for host, host_stats in unverified_stats.items():
            if not isinstance(host, str) or not isinstance(host_stats, dict):
                continue

            any_valid = False
            valid_host_stats = {}
            for category in ANSIBLE_STATS_CATEGORIES:
                value = host_stats.get(category, 0)
                valid_host_stats[category] = value
                if value != 0:
                    any_valid = True

            if any_valid:
                valid_stats[host] = valid_host_stats

        return valid_stats

    # pylint: disable=R0911
    def _get_last_stats(self) -> (None, dict):
        if not self._config.stats_live and not self._config.stats_recap:
            return None

        if self.finished and self._cache_last_stats is not None:
            # stats do not change once finished
            return self._cache_last_stats

        if self.finished and self._config.stats_recap:
            description = 'Recap-stats'
            prefix = SELECTOR_STATS_RECAP_BEGIN
            suffix = SELECTOR_STATS_RECAP_END

        elif self._config.stats_live:
            description = 'Live-stats'
            prefix = SELECTOR_STATS_LIVE_BEGIN
            suffix = SELECTOR_STATS_LIVE_END

        else:
            return None

        last_stats = self._get_last_occurrence_in_logs(tail_line_count=1000, line_start=prefix)
        if last_stats is None:
            if self._cache_last_stats is not None:
                return self._cache_last_stats

            return None

        stats_json = last_stats.strip().removeprefix(prefix).removesuffix(suffix)
        if self._config.debug:
            log(f"Last {description} from logs: '{stats_json}'")

        try:
            stats = self._build_valid_stats(json_loads(stats_json))
            self._cache_last_stats = stats
            return stats

        except JSONDecodeError as e:
            if self._config.debug:
                log(f"Failed to parse stats as JSON: '{stats_json}' => '{e}'")

            if self._cache_last_stats is not None:
                return self._cache_last_stats

            return None

    @property
    def stats(self) -> None|AnsiblePlaybookStatsByHost:
        return self._get_last_stats()

    @property
    def stats_by_category(self) -> None|AnsiblePlaybookStatsByCategory:
        stats_by_host = self.stats
        if stats_by_host is None:
            return None

        result: AnsiblePlaybookStatsByCategory = {
            'ok': {}, 'changed': {}, 'unreachable': {},
            'failures': {}, 'skipped': {}, 'rescued': {}, 'ignored': {}
        }

        for host, host_stats in stats_by_host.items():
            for category in ANSIBLE_STATS_CATEGORIES:
                result[category][host] = host_stats.get(category, 0)

        return result

    def time_duration_sec(self) -> int:
        if self.time_finish == -1:
            return int(time()) - self.time_start

        return self.time_finish - self.time_start

    @property
    def log_stdout_file(self) -> (Path, None):
        return self._config.log_stdout_file

    @property
    def log_stderr_file(self) -> (Path, None):
        return self._config.log_stderr_file

    def set_log_file_cleaned(self):
        self._log_stdout_stats_cleaned = True

    def _load_stdout_lines_from_log_file(self) -> list[str]:
        if self._cache_stdout_lines is not None:
            return self._cache_stdout_lines

        skip_line_prefixes = []
        if self._config.stats_live:
            skip_line_prefixes.append(SELECTOR_STATS_LIVE_BEGIN)

        if self._config.stats_recap:
            skip_line_prefixes.append(SELECTOR_STATS_RECAP_BEGIN)

        lines = []
        if self._config.log_stdout_file is None or not self._config.log_stdout_file.is_file():
            return lines

        with open(self._config.log_stdout_file, 'r', encoding='utf-8') as log_file:
            if self._log_stdout_stats_cleaned or len(skip_line_prefixes) == 0:
                return log_file.readlines()

            for line in log_file:
                skip = False
                for skip_prefix in skip_line_prefixes:
                    if line.startswith(skip_prefix):
                        skip = True
                        break

                if skip:
                    continue

                lines.append(line)

        if self.finished:
            # log-file does not change after process finished
            self._cache_stdout_lines = lines

        return lines

    @property
    def stdout_lines(self) -> (list[str], None):
        if not self._config.load_log_stdout or self._config.log_stdout_file is None:
            return None

        return self._load_stdout_lines_from_log_file()

    @property
    def stdout(self) -> (str, None):
        stdout_lines = self.stdout_lines
        if stdout_lines is None:
            return None

        return '\n'.join(stdout_lines)

    def _load_stderr_lines_from_log_file(self) -> list[str]:
        if self._cache_stderr_lines is not None:
            return self._cache_stderr_lines

        lines = []
        if self._config.log_stderr_file is None or not self._config.log_stderr_file.is_file():
            return lines

        with open(self._config.log_stderr_file, 'r', encoding='utf-8') as log_file:
            return log_file.readlines()

    @property
    def stderr_lines(self) -> (list[str], None):
        if not self._config.load_log_stderr or self._config.log_stderr_file is None:
            return None

        return self._load_stderr_lines_from_log_file()

    @property
    def stderr(self) -> (str, None):
        stderr_lines = self.stderr_lines
        if stderr_lines is None:
            return None

        return '\n'.join(stderr_lines)

    def to_dict(self) -> dict:
        return {
            'finished': self.finished,
            'playbook_finished': self.playbook_finished,
            'failed': self.failed,
            'canceled': self.canceled,
            'time_start': self.time_start,
            'time_finish': self.time_finish,
            'timed_out': self.timed_out,
            'stats': self.stats,
            'time_duration_sec': self.time_duration_sec(),
            'log_stdout_file': str(self.log_stdout_file),
            'log_stderr_file': str(self.log_stderr_file),
            'ansible_command': self.ansible_command,
            'process_command': self.process_command,
            'process_rc': self.process_rc,
            'process_result': self.process_result,
        }

    # pylint: disable=R0801
    def to_json(self, pretty: bool = False) -> str:
        indent = 0
        if pretty:
            indent = 2

        return json_dumps(self.to_dict(), default=str, indent=indent)

    def __repr__(self) -> str:
        return self.to_json(pretty=True)
