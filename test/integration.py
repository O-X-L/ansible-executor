#!/usr/bin/env python3

from time import sleep
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
            'output_color': False,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
    },
    {
        'name': 'Play1 - setting extra-vars',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test2'},
            'output_color': False,
        },
        'exception': None,
        'result': {'failed': True, 'finished': True, 'playbook_finished': True, 'timed_out': False},
    },
    {
        'name': 'Play1 - setting env-vars',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test2'},
            'env_vars': {'TEST2_VAR': 'SomeRandomValue'},
            'output_color': False,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
    },
    {
        'name': 'Play1 - output-color enabled',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': True,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_stdout': '\u001b[0;32m',
    },
    {
        'name': 'Play1 - user stops execution',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test3'},  # sleeps some time so we can kill it
            'output_color': False,
        },
        'exception': None,
        'blocking': False,
        'stop': True,
        'result': {'failed': True, 'finished': True, 'playbook_finished': False, 'timed_out': False},
        'in_stderr': 'User interrupted execution',
    },
    {
        'name': 'Play1 - execution timed-out',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test3'},  # sleeps some time so it can timeout
            'timeout_sec_run': 2,
            'output_color': False,
        },
        'exception': None,
        'blocking': True,
        'result': {'failed': True, 'finished': True, 'playbook_finished': False, 'timed_out': True},
        'in_stderr': 'timed out after',
    },
    {
        'name': 'Play1 - ansible-vault encrypted secret',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test5'},  # has a vault-secret configured
            'vault_pass_value': 'SuperSecret!',
            'output_color': False,
        },
        'exception': None,
        'blocking': True,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_stdout': 'This is Test5',
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
        e.run(blocking=test.get('blocking', True))

        if test.get('stop', False):
            sleep(1)
            log('[TEST-INFO] Stopping execution')
            e.stop()
            sleep(2)

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

    if 'in_stdout' in test:
        if test['in_stdout'] not in e.status.process_result.stdout:
            log(
                f"[TEST-ERROR] Required output not found: '{test['in_stdout']}'"
            )
            test_failure()
            if LOG_VERBOSE:
                sys_exit(1)

    if 'in_stderr' in test:
        if test['in_stderr'] not in e.status.process_result.stderr:
            log(
                f"[TEST-ERROR] Required error-output not found: '{test['in_stderr']}'"
            )
            test_failure()
            if LOG_VERBOSE:
                sys_exit(1)

    log('[TEST-SUCCESS] Test finished successfully!')
    test_success()
