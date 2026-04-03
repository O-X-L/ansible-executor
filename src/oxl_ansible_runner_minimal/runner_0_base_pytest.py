from shutil import rmtree
from tempfile import mkdtemp
from pathlib import Path

import pytest


PATH_TEST = Path(mkdtemp(prefix='ar_test'))


@pytest.fixture(autouse=True)
def run_before_and_after_tests(tmpdir):
    PATH_TEST.mkdir(exist_ok=True)
    with open(f'{PATH_TEST}/test.yml', 'wb') as f:
        f.write(b'')

    with open(f'{PATH_TEST}/test.yml', 'wb') as f:
        f.write(b'')

    (PATH_TEST / 'inv1').mkdir(exist_ok=True)
    (PATH_TEST / 'inv2').mkdir(exist_ok=True)
    with open(f'{PATH_TEST}/inv2/hosts', 'wb') as f:
        f.write(b'')

    yield

    rmtree(PATH_TEST)
