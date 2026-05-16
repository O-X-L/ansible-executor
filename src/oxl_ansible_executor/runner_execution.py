import os
from pathlib import Path
from copy import deepcopy
from threading import Thread
from tempfile import mkdtemp
from time import time, sleep
from shutil import chown, rmtree

from oxl_ansible_executor.runner_config import ExecutionConfig
from oxl_ansible_executor.exceptions import PreparationError
from oxl_ansible_executor.runner_executor_local import ExecutorBase, ExecutorLocal
from oxl_ansible_executor.runner_executor_container import ExecutorContainerDocker, ExecutorContainerPodman
from oxl_ansible_executor.utils.debug import log
from oxl_ansible_executor.utils.util import get_random_str
from oxl_ansible_executor.utils.filesystem import write_file_with_mode, overwrite_and_delete_file, get_file_opener_from_mode
from oxl_ansible_executor.config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN, DEFAULT_LOG_DIR, SELECTOR_STATS_RECAP_BEGIN, \
    SELECTOR_STATS_LIVE_BEGIN

from oxl_ansible_executor.runner_execution_status import ExecutionStatus


def _write_secret_to_pipe(file: str, secret: str):
    with open(file, 'w', encoding='utf-8') as f:
        f.write(secret)

    os.remove(file)


class Execution:
    # pylint: disable=R0902
    def __init__(self, config: ExecutionConfig):
        self.config: ExecutionConfig = deepcopy(config)  # make sure the source-config is re-usable and not modified

        self._status = ExecutionStatus(self.config)
        self.__started = False
        self._executor: ExecutorBase = None

        self.__cleaned_up = False
        self._prepare()
        self._execution_thread: Thread = None
        self._cleanup_thread: Thread = None

    @property
    def status(self) -> ExecutionStatus:
        return self._status

    def stop(self):
        self._executor.signal_stop = True

    def _prepare(self):
        self._run_id = f'{int(time())}_{get_random_str(5)}'
        self._cleanup_run_dir = False
        if self.config.run_dir is None:
            self._cleanup_run_dir = True
            self.config.run_dir = Path(mkdtemp(prefix='ar_'))

        # pylint: disable=W0212
        self.__secret_pipe_ssh_key = self._get_secret_pipe_or_none(self.config._ssh_key)
        self.__secret_pipe_connect_pass = self._get_secret_pipe_or_none(self.config._connect_pass)
        self.__secret_pipe_become_pass = self._get_secret_pipe_or_none(self.config._become_pass)
        self.__secret_pipe_vault_pass = self._get_secret_pipe_or_none(self.config._vault_pass)
        self._ssh_known_hosts_file = self._get_secret_pipe_or_none(self.config.ssh_known_hosts_file)
        self._secret_pipe_threads = []

        self._get_executor()

    def _get_secret_pipe_or_none(self, value: (str, None)) -> (None, Path):
        if value is None:
            return None

        return self.config.run_dir / f'.{get_random_str(10)}'

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
            run_id=self._run_id,
            pipe_ssh_key=self.__secret_pipe_ssh_key,
            pipe_connect_pass=self.__secret_pipe_connect_pass,
            pipe_become_pass=self.__secret_pipe_become_pass,
            pipe_vault_pass=self.__secret_pipe_vault_pass,
        )
        self._status.executor = self._executor
        if self.config.debug:
            log(f"Using executor: {name}")

    def run(self, blocking: bool = True) -> (None, ExecutionStatus):
        self.config.validate()

        if self.__started:
            raise PreparationError('A runner-execution should only be invoked once. Create a new one!')

        self.__started = True

        self._before()
        if blocking:
            self._execute_blocking()
            self._after()
            return self.status

        self._execute_non_blocking()
        return None

    def _before(self):
        self._copy_ssh_known_hosts_file()
        self._create_log_files()
        self._prepare_executor()
        self._create_secret_pipes()

    def _prepare_executor(self):
        self._executor.prepare()

    def _execute_blocking(self):
        if self.config.debug:
            log(f"Using log files: {self.config.log_stdout_file} & {self.config.log_stderr_file}")

        self._executor.execute()

    def _execute_non_blocking(self):
        self._execution_thread = Thread(target=self._execute_blocking)
        self._execution_thread.start()
        self._cleanup_thread = Thread(target=self._wait_for_after)
        self._cleanup_thread.start()

    def _wait_for_after(self):
        time_start = time()
        timeout = self.config.timeout_sec_run + 60  # make sure executor has some more time to end gracefully

        while not self.status.finished:
            sleep(0.1)
            if (time() - timeout) > time_start:
                if self.config.debug:
                    log('Execution timeout reached')

                break

        self._after()

    def _after(self):
        if self.config.debug:
            log('Post-execution tasks')

        self._clean_stats_sections_from_stdout_log()
        self.cleanup()

    def _create_secret_pipes(self):
        # pylint: disable=W0212
        if self.config.debug:
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

    def _create_secret_pipe(self, secret: (str, None), file: (Path, None)) -> None:
        if secret is None or file is None:
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
        if self.config.debug:
            log('Creating log-files')

        if not DEFAULT_LOG_DIR.is_dir():
            DEFAULT_LOG_DIR.mkdir(parents=True)

        if self.config.log_stdout_file is None:
            self.config.log_stdout_file = DEFAULT_LOG_DIR / f'ansible_{self._run_id}_stdout.log'

        if self.config.log_stderr_file is None:
            self.config.log_stderr_file = DEFAULT_LOG_DIR / f'ansible_{self._run_id}_stderr.log'

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

        if self.config.debug:
            log('Copying SSH-known-hosts file')

        with open(self.config.ssh_known_hosts_file, 'r', encoding='utf-8') as f:
            ssh_known_hosts = f.read()

        if self._ssh_known_hosts_file.exists():
            os.remove(self._ssh_known_hosts_file)

        write_file_with_mode(file=self._ssh_known_hosts_file, content=ssh_known_hosts, file_mode=0o600)

    def _clean_stats_sections_from_stdout_log(self):
        if self.config.debug:
            log('Cleaning stats-sections from log-files')

        if self.config.debug:
            return

        # make sure the stats are loaded and cached before we clean them from the logs
        _ = self.status.stats

        selectors_to_clean = []
        if self.config.stats_live:
            selectors_to_clean.append(SELECTOR_STATS_LIVE_BEGIN)

        if self.config.stats_recap:
            selectors_to_clean.append(SELECTOR_STATS_RECAP_BEGIN)

        if len(selectors_to_clean) == 0:
            return

        self._clean_stats_sections_from_stdout_log_io(selectors_to_clean)
        self.status.set_log_file_cleaned()

    def _clean_stats_sections_from_stdout_log_io(self, selectors_begin: list[str]):
        tmp_log_file = f'{self.config.log_stdout_file}.tmp'
        opener = get_file_opener_from_mode(self.config.log_file_mode)

        try:
            with (
                open(self.config.log_stdout_file, 'r', encoding='utf-8') as infile,
                open(tmp_log_file, 'w', encoding='utf-8', opener=opener) as outfile,
            ):
                for line in infile:
                    skip = False
                    for selector_begin in selectors_begin:
                        if line.startswith(selector_begin):
                            skip = True
                            break

                    if skip:
                        continue

                    outfile.write(line)

            os.replace(tmp_log_file, self.config.log_stdout_file)

        except FileNotFoundError:
            if os.path.exists(tmp_log_file):
                os.remove(tmp_log_file)

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
        if self._cleanup_run_dir:
            rmtree(self.config.run_dir)

        for t in self._secret_pipe_threads:
            t.join()

        self.__cleaned_up = True

    def __del__(self):
        self.cleanup()
