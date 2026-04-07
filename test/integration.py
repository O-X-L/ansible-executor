#!/usr/bin/env python3

from time import sleep
from pathlib import Path
from tempfile import mktemp
from os import environ
from os import remove as remove_file
from sys import exit as sys_exit
from atexit import register as run_at_exit

from oxl_ansible_executor import Execution, ExecutionConfig, \
    ConfigError, SetupError, PreparationError, ExecutionError

# SETUP

PATH_TESTDATA = Path(__file__).parent.parent / 'testdata'
LOG_VERBOSE = environ.get('AR_TEST_VERBOSE', '1') == '1'  # set env-var to 0 to only get brief results
environ.setdefault('ANSIBLE_LOCALHOST_WARNING', '0')

SSH_KEY_FILE = mktemp(prefix='ar_test_')
CONNECT_PWD_FILE = mktemp(prefix='ar_test_')
BECOME_PWD_FILE = mktemp(prefix='ar_test_')
VAULT_PWD_FILE = mktemp(prefix='ar_test_')
with open(SSH_KEY_FILE, 'wb') as f:
    f.write(b'''-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACCx05E0HFxCKLvd6he9EpvQnv+nzlCCo5dbEGLkiD0gyQAAAJD9i8+W/YvP
lgAAAAtzc2gtZWQyNTUxOQAAACCx05E0HFxCKLvd6he9EpvQnv+nzlCCo5dbEGLkiD0gyQ
AAAEAJ5zfDQBaEbidne6fHzaTif4Rdud5vveMfveWVx72G4rHTkTQcXEIou93qF70Sm9Ce
/6fOUIKjl1sQYuSIPSDJAAAACXJhdGhAZ2F0ZQECAwQ=
-----END OPENSSH PRIVATE KEY-----
''')  # NOTE: this is a dummy-key just created for this test

with open(CONNECT_PWD_FILE, 'wb') as f:
    f.write(b'connect-placeholder')

with open(BECOME_PWD_FILE, 'wb') as f:
    f.write(b'become-placeholder')

with open(VAULT_PWD_FILE, 'wb') as f:
    f.write(b'SuperSecret!')


def cleanup_tmpfiles():
    remove_file(SSH_KEY_FILE)
    remove_file(CONNECT_PWD_FILE)
    remove_file(BECOME_PWD_FILE)
    remove_file(VAULT_PWD_FILE)


run_at_exit(cleanup_tmpfiles)

# TEST CONFIG

TESTS = [
    {
        'name': 'Basic targeting localhost',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False, 'canceled': False},
    },
    {
        'name': 'Using extra-vars',
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
        'name': 'Using env-vars',
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
        'name': 'Output-color enabled',
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
        'name': 'User stops execution',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test3'},  # sleeps some time so we can kill it
            'output_color': False,
        },
        'exception': None,
        'blocking': False,
        'stop': True,
        'result': {'failed': True, 'finished': True, 'playbook_finished': False, 'timed_out': False, 'canceled': True},
        'in_stderr': 'User interrupted execution',
    },
    {
        'name': 'Execution timed-out',
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
        'name': 'Ansible-vault encrypted secret (as vault_pass_value)',
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
    {
        'name': 'Ansible-vault encrypted secret (as vault_pass_file)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'extra_vars': {'test': 'test5'},  # has a vault-secret configured
            'vault_pass_file': VAULT_PWD_FILE,
            'output_color': False,
        },
        'exception': None,
        'blocking': True,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_stdout': 'This is Test5',
        'in_cmd': ['--vault-pass-file'],
    },
    {
        'name': 'Using connect-pass-file (without requiring it)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
            'connect_pass_file': CONNECT_PWD_FILE,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_cmd': ['--conn-pass-file'],
    },
    {
        'name': 'Using become-pass-file (without requiring it)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
            'become_pass_file': BECOME_PWD_FILE,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_cmd': ['--become-pass-file'],
    },
    {
        'name': 'Using ssh-key-file (without requiring it)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
            'ssh_key_file': SSH_KEY_FILE,
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_stderr': 'Identity added',
    },
    {
        'name': 'Using connect-user (without requiring it)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
            'connect_user': 'userConnect',
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_cmd': ['-u userConnect'],
    },
    {
        'name': 'Using become-user (without requiring it)',
        'config': {
            'playbook_dir': PATH_TESTDATA,
            'playbook_file': 'play1.yml',
            'output_color': False,
            'become_user': 'userBecome',
        },
        'exception': None,
        'result': {'failed': False, 'finished': True, 'playbook_finished': True, 'timed_out': False},
        'in_cmd': ['--become-user userBecome'],
    },
]

# TEST LOGIC

def log(msg: str):
    if LOG_VERBOSE:
        print(msg)


def test_success(nr: int):
    print(f'☑ Success: {nr}')


def test_failure(nr: int):
    print(f'☒ Failed: {nr}')


for test_nr, test in enumerate(TESTS):
    log('####################')
    log(f"[TEST-INFO] TEST: '{test['name']}'")

    try:
        log('[TEST-INFO] Init config')
        c = ExecutionConfig(**test['config'], debug=LOG_VERBOSE)

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
            test_failure(test_nr)
            if LOG_VERBOSE:
                raise

            continue

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
            test_failure(test_nr)
            if LOG_VERBOSE:
                sys_exit(1)

            continue

    if 'in_stdout' in test:
        if test['in_stdout'] not in e.status.process_result.stdout:
            log(
                f"[TEST-ERROR] Required output not found: '{test['in_stdout']}'"
            )
            test_failure(test_nr)
            if LOG_VERBOSE:
                sys_exit(1)

            continue

    if 'in_stderr' in test:
        if test['in_stderr'] not in e.status.process_result.stderr:
            log(
                f"[TEST-ERROR] Required error-output not found: '{test['in_stderr']}'"
            )
            test_failure(test_nr)
            if LOG_VERBOSE:
                sys_exit(1)

            continue

    if 'in_cmd' in test:
        cmd = ' '.join(e.status.process_command)
        for in_cmd in test['in_cmd']:
            if in_cmd not in cmd:
                log(
                    f"[TEST-ERROR] Required command-substring not found: '{test['in_cmd']}' ({cmd})"
                )
                test_failure(test_nr)
                if LOG_VERBOSE:
                    sys_exit(1)

                continue

    log('[TEST-SUCCESS] Test finished successfully!')
    test_success(test_nr)
