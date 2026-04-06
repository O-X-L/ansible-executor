#!/usr/bin/env python3

from os import environ
from pathlib import Path
from sys import exit as sys_exit

from oxl_ansible_executor import Execution, ExecutionConfig, \
    ConfigError, SetupError, PreparationError, ExecutionError

PATH_TESTDATA = Path(__file__).parent.parent / 'testdata'
LOG_VERBOSE = environ.get('AR_TEST_VERBOSE', '1') == '1'  # set env-var to 0 to only get brief results

TESTS = [
    {
        'name': 'Play1 - basic targeting localhost',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
        },
        'exception': None,
        'result': {'failed': False},
    },
    {
        'name': 'Play1 - setting extra-vars',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'run2'},
        },
        'exception': None,
        'result': {'failed': True},
    },
    {
        'name': 'Play1 - setting env-vars',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'run2'},
            'env_vars': {'TEST1_VAR2': 'SomeRandomValue'},
        },
        'exception': None,
        'result': {'failed': False},
    },
]


def log(msg: str):
    if LOG_VERBOSE:
        print(msg)


def test_success():
    print('☑ Success')


def test_failure():
    print('☒ Failed')


for test in TESTS:
    log('####################')
    log(f"[TEST-INFO] TEST: '{test['name']}'")

    try:
        log('[TEST-INFO] Init config')
        c = ExecutionConfig(**test['config'], silent=not LOG_VERBOSE)

        log('[TEST-INFO] Init execution')
        e = Execution(c)

        log('[TEST-INFO] Run execution')
        e.run()

    except (ConfigError, SetupError, PreparationError, ExecutionError) as e:
        if test['exception'] is None:
            log('[TEST-ERROR] Got unexpected error')
            if LOG_VERBOSE:
                raise

        # pylint: disable=W1116
        if not isinstance(e, test['exception']):
            log('[TEST-ERROR] Got unexpected error')
            test_failure()
            if LOG_VERBOSE:
                raise

    log('[TEST-INFO] Result:')
    log(e.status)

    log('[TEST-INFO] Checking result')
    for attr, want_value in test['result'].items():
        if not hasattr(e.status, attr):
            log(f"[TEST-WARNING] Test has unknown execution.result attribute configured: '{attr}'")
            continue

        got_value = getattr(e.status, attr)
        if got_value != want_value:
            log(
                f"[TEST-ERROR] Test-Result got unexpected status: '{attr}' - want '{want_value}' - got '{got_value}'"
            )
            test_failure()
            if LOG_VERBOSE:
                sys_exit(1)

    log('[TEST-SUCCESS] Test finished successfully!')
    test_success()
