from sys import stdout
from json import dumps as json_dumps

from ansible.plugins.callback import CallbackBase
from ansible.executor.stats import AggregateStats

SELECTOR_STATS_RECAP_BEGIN = '__AR_STATS_RECAP_BEGIN__'
SELECTOR_STATS_RECAP_END = '__AR_STATS_RECAP_END__'


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'oxl_executor_stats_recap'
    CALLBACK_NEEDS_WHITELIST = True

    def v2_playbook_on_stats(self, stats: AggregateStats):
        host_stats = {}
        for host in stats.processed.keys():
            host_stats[host] = stats.summarize(host)

        payload = json_dumps(host_stats)
        stdout.write("\n" + SELECTOR_STATS_RECAP_BEGIN + payload + SELECTOR_STATS_RECAP_END + "\n")
        stdout.flush()
