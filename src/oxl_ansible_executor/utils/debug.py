from os import getpid
from datetime import datetime
from inspect import stack as inspect_stack
from inspect import getfile as inspect_getfile

from config import LOG_TIME_FORMAT

PID = getpid()


def log(msg: str):
    caller = inspect_getfile(inspect_stack()[1][0]).rsplit('/', 1)[1].rsplit('.', 1)[0]
    print(f'[{datetime.now().strftime(LOG_TIME_FORMAT)}] [{PID}] [DEBUG] [{caller}] {msg}')
