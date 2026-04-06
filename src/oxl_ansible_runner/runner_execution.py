import os
from time import time
from pathlib import Path
from copy import deepcopy
from threading import Thread
from tempfile import mkdtemp
from shutil import chown, rmtree
from json import dumps as json_dumps

from runner_config import ExecutionConfig
from exceptions import PreparationError
from config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN, DEFAULT_LOG_DIR
from runner_executor_local import ExecutorBase, ExecutorLocal
from runner_executor_container import ExecutorContainerDocker, ExecutorContainerPodman
from utils.debug import log
from utils.subps import ProcessResult
from utils.util import get_random_str
from utils.filesystem import write_file_with_mode, overwrite_and_delete_file


class ExecutionStatus:
    def __init__(self, config: ExecutionConfig):
        self._config: ExecutionConfig = config
        self.time_start = int(time())
        self._executor: ExecutorBase = None

    # todo: use properties to add executor-infos to execution-status
    @property
    def executor(self) -> None:
        return None

    @executor.setter
    def executor(self, executor: ExecutorBase):
        self._executor = executor

    @property
    def time_finish(self) -> int:
        return self._executor.time_finish

    @property
    def process_command(self) -> (None, list[str]):
        if self._executor is None:
            return None

        return self._executor.command

    @property
    def process_rc(self) -> int:
        if self._executor is None or self._executor.result is None:
            return -1

        return self._executor.result.rc

    @property
    def process_result(self) -> (ProcessResult, None):
        if self._executor is None or self._executor.result is None:
            return None

        return self._executor.result

    @property
    def finished(self) -> bool:
        return self.process_rc != -1

    @property
    def failed(self) -> bool:
        if not self.finished:
            return False

        if self.process_result is None:
            # bug? should not happen
            return True

        return self.process_rc != 0

    @property
    def playbook_finished(self) -> bool:
        max_lines_scan = 100
        if not self.finished or self.process_result is None:
            return False

        stdout_reversed = self.process_result.stdout_lines.copy()
        stdout_reversed.reverse()
        for i, line in enumerate(stdout_reversed):
            if i > max_lines_scan:
                break

            if line.startswith('PLAY RECAP'):
                return True

        return False

    def time_duration_sec(self) -> int:
        if self.time_finish == -1:
            return int(time()) - self.time_start

        return self.time_finish - self.time_start

    @property
    def log_stdout_file(self) -> (Path, None):
        return self._config.log_stdout_file

    @property
    def log_stderr_file(self) -> (Path, None):
        return self._config.log_stderr_file

    def to_dict(self) -> dict:
        return {
            'finished': self.finished,
            'playbook_finished': self.playbook_finished,
            'failed': self.failed,
            'time_start': self.time_start,
            'time_finish': self.time_finish,
            'time_duration_sec': self.time_duration_sec(),
            'log_stdout_file': str(self.log_stdout_file),
            'log_stderr_file': str(self.log_stderr_file),
            'process_command': self.process_command,
            'process_rc': self.process_rc,
            'process_result': self.process_result.to_dict(),
        }

    def to_json(self) -> str:
        return json_dumps(self.to_dict(), default=str, indent=2)

    def __repr__(self) -> str:
        return self.to_json()


def _write_secret_to_pipe(file: str, secret: str):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(secret)

    os.remove(file)


class Execution:
    # pylint: disable=R0902
    def __init__(self, config: ExecutionConfig):
        self.config = deepcopy(config)  # make sure the source-config is re-usable and not modified

        self._status = ExecutionStatus(self.config)
        self.__started = False
        self._executor: ExecutorBase = None

        self.__cleaned_up = False
        self._prepare()

    @property
    def status(self) -> ExecutionStatus:
        return self._status

    def stop_execution(self):
        self._executor.signal_stop = True

    def _prepare(self):
        if self.config.run_dir is None:
            self._path_run = Path(mkdtemp(prefix='ar_'))

        else:
            self._path_run = self.config.run_dir

        self.__secret_pipe_ssh_key = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_connect_pass = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_become_pass = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_vault_pass = self._path_run / f'.{get_random_str(20)}'
        self._secret_pipe_threads = []
        self._ssh_known_hosts_file = self._path_run / f'.{get_random_str(20)}'

    def run(self) -> ExecutionStatus:
        self.config.validate()

        if self.__started:
            raise PreparationError('A runner-execution should only be invoked once. Create a new one!')

        self.__started = True

        self._before()
        self._execute()
        self._after()

        return self.status

    def _before(self):
        self._copy_ssh_known_hosts_file()
        self._create_log_files()
        self._get_executor()
        self._prepare_executor()
        self._create_secret_pipes()

    def _get_executor(self):
        executor = ExecutorLocal
        name = 'local'
        if self.config.containerized:
            if self.config.container_engine == CONTAINER_ENGINE_DOCKER:
                executor = ExecutorContainerDocker
                name = 'docker'

            elif self.config.container_engine == CONTAINER_ENGINE_PODMAN:
                executor = ExecutorContainerPodman
                name = 'podman'

        self._executor = executor(
            config=self.config,
            pipe_ssh_key=self.__secret_pipe_ssh_key,
            pipe_connect_pass=self.__secret_pipe_connect_pass,
            pipe_become_pass=self.__secret_pipe_become_pass,
            pipe_vault_pass=self.__secret_pipe_vault_pass,
        )
        self._status.executor = self._executor
        log(f"Using executor: {name}")

    def _prepare_executor(self):
        self._executor.prepare_engine()

    def _execute(self):
        self._executor.execute()

    def _after(self):
        self.cleanup()

    def _create_secret_pipes(self):
        # pylint: disable=W0212
        log('Creating secret-pipes')
        self._create_secret_pipe(
            secret=self.config._ssh_key,
            file=self.__secret_pipe_ssh_key,
        )
        self._create_secret_pipe(
            secret=self.config._connect_pass,
            file=self.__secret_pipe_connect_pass,
        )
        self._create_secret_pipe(
            secret=self.config._become_pass,
            file=self.__secret_pipe_become_pass,
        )
        self._create_secret_pipe(
            secret=self.config._vault_pass,
            file=self.__secret_pipe_vault_pass,
        )

    def _create_secret_pipe(self, secret: (str, None), file: Path) -> None:
        if secret is None:
            return

        if file.exists():
            os.remove(file)

        os.mkfifo(file, mode=0o600)
        t = Thread(
            target=_write_secret_to_pipe,
            kwargs={'file': file, 'secret': secret},
        )
        t.start()
        self._secret_pipe_threads.append(t)

    def _create_log_files(self):
        log('Creating log-files')
        if not DEFAULT_LOG_DIR.is_dir():
            DEFAULT_LOG_DIR.mkdir(parents=True)

        log_file_id = f'{int(time())}_{get_random_str(5)}'
        if self.config.log_stdout_file is None:
            self.config.log_stdout_file = DEFAULT_LOG_DIR / f'ansible_stdout_{log_file_id}.log'

        if self.config.log_stderr_file is None:
            self.config.log_stderr_file = DEFAULT_LOG_DIR / f'ansible_stderr_{log_file_id}.log'

        self._create_log_file(which_file='stdout', file=self.config.log_stdout_file)
        self._create_log_file(which_file='stderr', file=self.config.log_stderr_file)

    def _create_log_file(self, which_file: str, file: Path) -> None:
        if file.is_file():
            raise PreparationError(f"Provided 'log_{which_file}_file' should not be an existing file! ({file})")

        write_file_with_mode(file=file, content='', file_mode=self.config.log_file_mode)

        if self.config.log_file_owner_group is not None:
            try:
                chown(path=file, group=self.config.log_file_owner_group)

            except LookupError:
                raise PreparationError("Provided 'log_file_owner_group' does not exist!")

    def _copy_ssh_known_hosts_file(self):
        if self.config.ssh_known_hosts_file is None:
            return

        log('Copying SSH-known-hosts file')
        with open(self.config.ssh_known_hosts_file, 'r', encoding='utf-8') as f:
            ssh_known_hosts = f.read()

        if self._ssh_known_hosts_file.exists():
            os.remove(self._ssh_known_hosts_file)

        write_file_with_mode(file=self._ssh_known_hosts_file, content=ssh_known_hosts, file_mode=0o600)

    def cleanup(self):
        # is done automatically after:
        #   the ansible-playbook ended
        #   the Runner instance has been deleted

        if self.__cleaned_up:
            return

        overwrite_and_delete_file(self.__secret_pipe_ssh_key)
        overwrite_and_delete_file(self.__secret_pipe_connect_pass)
        overwrite_and_delete_file(self.__secret_pipe_become_pass)
        overwrite_and_delete_file(self._ssh_known_hosts_file)
        if self.config.run_dir is None:
            rmtree(self._path_run)

        for t in self._secret_pipe_threads:
            t.join()

        self.__cleaned_up = True

    def __del__(self):
        self.cleanup()
