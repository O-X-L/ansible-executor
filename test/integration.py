#!/usr/bin/env python3

from pathlib import Path
from sys import exit as sys_exit

from oxl_ansible_executor import Execution, ExecutionConfig, \
    ConfigError, SetupError, PreparationError, ExecutionError

PATH_TESTDATA = Path(__file__).parent.parent / 'testdata'

TESTS = [
    {
        'name': 'Play1 targeting localhost',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
        },
        'exception': None,
        'result': {'failed': False},
    },
]

for test in TESTS:
    print('####################')
    print(f"[TEST-INFO] TEST: '{test['name']}'")

    try:
        print('[TEST-INFO] Init config')
        c = ExecutionConfig(**test['config'])

        print('[TEST-INFO] Init execution')
        e = Execution(c)

        print('[TEST-INFO] Run execution')
        e.run()

    except (ConfigError, SetupError, PreparationError, ExecutionError) as e:
        if test['exception'] is None:
            print('[TEST-ERROR] Got unexpected error')
            raise

        # pylint: disable=W1116
        if not isinstance(e, test['exception']):
            print('[TEST-ERROR] Got unexpected error')
            raise

    print('[TEST-INFO] Result:')
    print(e.status)

    print('[TEST-INFO] Checking result')
    for attr, want_value in test['result'].items():
        if not hasattr(e.status, attr):
            print(f"[TEST-WARNING] Test has unknown execution.result attribute configured: '{attr}'")
            continue

        got_value = getattr(e.status, attr)
        if got_value != want_value:
            print(
                f"[TEST-ERROR] Test-Result got unexpected status: '{attr}' - want '{want_value}' - got '{got_value}'"
            )
            sys_exit(1)

    print('[TEST-SUCCESS] Test finished successfully!')
