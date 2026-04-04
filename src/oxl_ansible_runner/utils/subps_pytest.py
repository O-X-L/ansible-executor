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
    from utils.subps import ProcessArgs, Process
    cmd = kwargs.pop('cmd')
    p = Process(cmd=cmd, args=ProcessArgs(**kwargs))
    p.start()
    r = p.wait_until_finished()
    p.close()

    assert r.rc == want['rc']
    assert r.stdout == want['stdout']
    assert r.stderr == want['stderr'] or (
            isinstance(r.stderr, str) and
            isinstance(want['stderr'], str) and
            want['stderr'] in r.stderr
    )

    with open(kwargs['file_stdout'], 'r', encoding='utf-8') as f:
        want_stdout = want['stdout'] if want['stdout'] is not None else ''
        is_stdout = f.read().strip()
        assert want_stdout in is_stdout

    with open(kwargs['file_stderr'], 'r', encoding='utf-8') as f:
        want_stderr = want['stderr'] if want['stderr'] is not None else ''
        is_stderr = f.read().strip()
        assert want_stderr in is_stderr
