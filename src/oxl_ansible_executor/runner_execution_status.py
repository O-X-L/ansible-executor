from time import time
from pathlib import Path
from json import dumps as json_dumps

from utils.subps import ProcessResult
from runner_config import ExecutionConfig
from runner_executor_local import ExecutorBase


class ExecutionStatus:
    def __init__(self, config: ExecutionConfig):
        self._config: ExecutionConfig = config
        self.time_start = int(time())
        self._executor: ExecutorBase = None

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
    def process_result(self) -> (ProcessResult, None):
        if self._executor is None or self._executor.result is None:
            return None

        return self._executor.result

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

    @property
    def playbook_finished(self) -> bool:
        max_lines_scan = 100
        if not self.finished or self.process_result is None:
            return False

        stdout_reversed = self.process_result.stdout_lines.copy()
        stdout_reversed.reverse()
        for i, line in enumerate(stdout_reversed):
            if i > max_lines_scan:
                break

            if line.startswith('PLAY RECAP'):
                return True

        return False

    @property
    def stats(self) -> dict:
        # todo: parse 'PLAY RECAP' or do it like the official ansible-executor and parse the streamed output?
        return {}

    @property
    def stats_by_category(self) -> dict:
        # todo: group by categories - ok, changed, unreachable, failed, skipped, rescued, ignored
        return self.stats

    @property
    def stats_by_hosts(self) -> dict:
        # todo: group by hosts
        return self.stats

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

    def to_dict(self) -> dict:
        return {
            'finished': self.finished,
            'playbook_finished': self.playbook_finished,
            'failed': self.failed,
            'canceled': self.canceled,
            'time_start': self.time_start,
            'time_finish': self.time_finish,
            'timed_out': self.timed_out,
            'time_duration_sec': self.time_duration_sec(),
            'log_stdout_file': str(self.log_stdout_file),
            'log_stderr_file': str(self.log_stderr_file),
            'ansible_command': self.ansible_command,
            'process_command': self.process_command,
            'process_rc': self.process_rc,
            'process_result': self.process_result.to_dict(),
        }

    # pylint: disable=R0801
    def to_json(self, pretty: bool = False) -> str:
        indent = 0
        if pretty:
            indent = 2

        return json_dumps(self.to_dict(), default=str, indent=indent)

    def __repr__(self) -> str:
        return self.to_json(pretty=True)
