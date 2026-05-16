from os import remove as remove_file

import pytest

# pylint: disable=C0415

TEST_LOG_STDERR = '/tmp/ar_test_stderr.log'
TEST_LOG_STDOUT = '/tmp/ar_test_stdout.log'

@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    with open(TEST_LOG_STDERR, 'wb') as f:
        f.write(b'')

    with open(TEST_LOG_STDOUT, 'wb') as f:
        f.write(b'')

    yield

    remove_file(TEST_LOG_STDERR)
    remove_file(TEST_LOG_STDOUT)


@pytest.mark.parametrize('kwargs, want', [
    (
            {'cmd': 'echo abc', 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': 'abc', 'stderr': None},
    ),
    (
            {'cmd': ['echo', 'abc'], 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': 'abc', 'stderr': None},
    ),
    (
            {'cmd': ['echo', 'abc'], 'shell': True, 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': 'abc', 'stderr': None},
    ),
    (
            {'cmd': 'echo abc', 'shell': True, 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': 'abc', 'stderr': None},
    ),
    (
            {'cmd': 'sleep 1', 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': None, 'stderr': None},
    ),
    (
            {'cmd': 'sleep 1', 'timeout_sec': 0, 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 1, 'stdout': None, 'stderr': 'timed out'},
    ),
    (
            {'cmd': 'sleep 1', 'timeout_sec': 0, 'shell': True, 'file_stdout': TEST_LOG_STDOUT,
             'file_stderr': TEST_LOG_STDERR},
            {'rc': 1, 'stdout': None, 'stderr': 'timed out'},
    ),
    (
            {'cmd': 'sleep 1', 'timeout_sec': 0, 'shell': True, 'timeout_shell': False,
             'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 1, 'stdout': None, 'stderr': 'timed out'},
    ),
    (
            {'cmd': 'mkdir /tmp/abc/def/ghi', 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 1, 'stdout': None, 'stderr': 'No such file or directory'},
    ),
    (
            {'cmd': 'echo', 'empty_none': False, 'file_stdout': TEST_LOG_STDOUT, 'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': '', 'stderr': ''},
    ),
    (
            {'cmd': 'cat', 'shell': True, 'stdin': 'test123', 'file_stdout': TEST_LOG_STDOUT,
             'file_stderr': TEST_LOG_STDERR},
            {'rc': 0, 'stdout': 'test123', 'stderr': None},
    ),
])
def test_subps_with_logfiles(kwargs: dict, want: dict):
    from oxl_ansible_executor.utils.subps import ProcessArgs, Process
    cmd = kwargs.pop('cmd')
    p = Process(cmd=cmd, args=ProcessArgs(**kwargs))
    p.start()
    r = p.wait_until_finished()
    p.close()

    expected_empty = '' if kwargs.get('empty_none', True) is False else None

    assert r.rc == want['rc']
    assert r.stdout == expected_empty
    assert r.stderr == expected_empty

    if want.get('stdout') is not None:
        with open(kwargs['file_stdout'], 'r') as f:
            assert f.read().strip() == want['stdout'].strip()

    if want.get('stderr') is not None:
        with open(kwargs['file_stderr'], 'r') as f:
            file_content = f.read().strip()
            assert want['stderr'].strip() in file_content or file_content in want['stderr'].strip()
