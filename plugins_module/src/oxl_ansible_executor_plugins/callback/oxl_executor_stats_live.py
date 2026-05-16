from time import time
from os import environ
from sys import stdout
from json import dumps as json_dumps

from ansible.plugins.callback import CallbackBase
from ansible.executor.task_result import TaskResult

SELECTOR_STATS_LIVE_BEGIN = '__AR_STATS_LIVE_BEGIN__'
SELECTOR_STATS_LIVE_END = '__AR_STATS_LIVE_END__'


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'oxl_executor_stats_live'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super().__init__()
        self.host_stats = {}
        self.last_emit_time = 0

        try:
            self.emit_interval = float(environ.get('AR_STATS_INTERVAL', 10.0))

        except ValueError:
            self.emit_interval = 10.0

    def _update_and_maybe_emit(self, host, status):
        if host not in self.host_stats:
            self.host_stats[host] = {}

        if status not in self.host_stats[host]:
            self.host_stats[host][status] = 0

        self.host_stats[host][status] += 1

        current_time = time()
        if (current_time - self.last_emit_time) >= self.emit_interval:
            self._emit()
            self.last_emit_time = current_time

    def _emit(self):
        payload = json_dumps(self.host_stats)
        stdout.write("\n" + SELECTOR_STATS_LIVE_BEGIN + payload + SELECTOR_STATS_LIVE_END + "\n")
        stdout.flush()

    # pylint: disable=W0212
    def v2_runner_on_ok(self, result: TaskResult):
        if result._result.get('changed', False):
            self._update_and_maybe_emit(result._host.get_name(), 'changed')

        else:
            self._update_and_maybe_emit(result._host.get_name(), 'ok')

    def v2_runner_on_failed(self, result: TaskResult, ignore_errors: bool = False):
        if ignore_errors:
            self._update_and_maybe_emit(result._host.get_name(), 'ignored')

        else:
            self._update_and_maybe_emit(result._host.get_name(), 'failures')

    def v2_runner_on_skipped(self, result: TaskResult):
        self._update_and_maybe_emit(result._host.get_name(), 'skipped')

    def v2_runner_on_unreachable(self, result: TaskResult):
        self._update_and_maybe_emit(result._host.get_name(), 'unreachable')
