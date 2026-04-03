import os
from pathlib import Path
from threading import Thread
from tempfile import mkdtemp
from time import sleep, time
from json import dumps as json_dumps
from shutil import chown, rmtree

from runner_config import Config
from exceptions import PreparationError
from utils.debug import log
from utils.util import get_random_str
from utils.filesystem import write_file_with_mode, overwrite_and_delete_file


def _close_secret_pipes_after_read(wait_sec: int, fds: list):
    sleep(wait_sec)
    log('Closing secret-pipes (start_pipe_block_sec)')
    for fd in fds:
        try:
            os.close(fd)

        except OSError:
            pass


class ExecutionStatus:
    def __init__(self):
        self.finished = False
        self.failed = False
        self.time_start = int(time())
        self.time_finish: int = 0

    def time_duration_sec(self) -> int:
        if self.time_finish == 0:
            return int(time()) - self.time_start

        return self.time_finish - self.time_start


class Execution:
    def __init__(self, config: Config):
        self.config = config

        self.status = ExecutionStatus()
        self.__started = False
        self.signal_stop = False

        self.__cleaned_up = False
        self._prepare()

    def _prepare(self):
        if self.config.run_dir is None:
            self._path_run = Path(mkdtemp(prefix='ar_'))

        else:
            self._path_run = self.config.run_dir

        self.__secret_pipe_ssh_key = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_connect_pass = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_become_pass = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_vault_pass = self._path_run / f'.{get_random_str(20)}'
        self.__secret_pipe_fds = []
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
        self._create_secret_pipes()

    def _execute(self):
        log('Executing ansible-playbook')
        cmd_ansible = self.generate_ansible_command()
        print(cmd_ansible)

        # execute playbook
        sleep(30)  # process-monitor loop - act on signals

    def _after(self):
        self.status.time_finish = int(time())
        self.status.finished = True

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

        if 'AR_TEST' not in os.environ:
            t = Thread(
                target=_close_secret_pipes_after_read,
                kwargs={'fds': self.__secret_pipe_fds, 'wait_sec': self.config.start_pipe_block_sec},
            )
            t.start()

    def _create_secret_pipe(self, secret: (str, None), file: Path) -> None:
        if secret is None:
            return

        if file.exists():
            os.remove(file)

        os.mkfifo(file, mode=0o600)
        fd_write = os.open(file, os.O_RDWR | os.O_NONBLOCK)
        os.write(fd_write, secret.encode('utf-8'))
        self.__secret_pipe_fds.append(fd_write)
        return

    def _create_log_files(self):
        log('Creating log-files')
        if self.config.log_stdout_file is None:
            self.config.log_stdout_file = self._path_run / f'ansible_stdout_{int(time())}.log'

        if self.config.log_stderr_file is None:
            self.config.log_stderr_file = self._path_run / f'ansible_stderr_{int(time())}.log'

        self._create_log_file(which_file='stdout', file=self.config.log_stdout_file)
        self._create_log_file(which_file='stderr', file=self.config.log_stderr_file)

    def _create_log_file(self, which_file: str, file: Path) -> None:
        if file.is_file():
            raise PreparationError(f"Provided 'log_{which_file}_file' should not be an existing file!")

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

    def generate_ansible_command(self) -> list[str]:
        # cleaned-up & simplified version of the official "ansible_runner.RunnerConfig.generate_ansible_command"
        # pylint: disable=R0912
        cmd = ['ansible-playbook']

        if self.config.inventory_files is not None:
            for i in self.config.inventory_files:
                cmd.extend(['-i', str(i)])

        if self.config.mode_check:
            cmd.append('--check')

        if self.config.mode_diff:
            cmd.append('--diff')

        if self.config.limit is not None:
            cmd.extend(['--limit', self.config.limit])

        if self.config.extra_vars is not None and len(self.config.extra_vars) > 0:
            extra_vars_list = []
            for k in self.config.extra_vars:
                extra_vars_list.append(f"\"{k}\":{json_dumps(self.config.extra_vars[k])}")

            cmd.extend(
                [
                    '-e',
                    f'{{{",".join(extra_vars_list)}}}'
                ]
            )

        if self.config.verbosity is not None:
            cmd.append(f'-{self.config.verbosity}')

        if self.config.tags is not None:
            cmd.extend(['--tags', self.config.tags])

        if self.config.skip_tags is not None:
            cmd.extend(['--skip-tags', self.config.skip_tags])

        if self.config.ssh_known_hosts_file is not None:
            cmd.extend([
                '-e',
                f"ansible_ssh_extra_args='-o UserKnownHostsFile={self.config.ssh_known_hosts_file}'",
            ])

        # pylint: disable=W0212
        if self.config._ssh_key is not None:
            cmd.extend(['--private-key', str(self.__secret_pipe_connect_pass)])

        if self.config.connect_user is not None:
            cmd.extend(['--user', self.config.connect_user])

        if self.config._connect_pass is not None:
            cmd.extend(['--connection-password-file', str(self.__secret_pipe_connect_pass)])

        if self.config.become_user is not None:
            cmd.extend(['--become-user', self.config.become_user])

        if self.config._become_pass is not None:
            cmd.extend(['--become-password-file', str(self.__secret_pipe_become_pass)])

        if self.config._vault_pass is not None:
            cmd.extend(['--vault-password-file', str(self.__secret_pipe_vault_pass)])

        if self.config.cmd_args is not None:
            cmd.extend(self.config.cmd_args)

        cmd.append(str(self.config.playbook_file))
        return cmd

    def cleanup(self):
        # is done automatically after:
        #   the ansible-playbook ended
        #   the Runner instance has been deleted

        if self.__cleaned_up:
            return

        for fd in self.__secret_pipe_fds:
            try:
                os.close(fd)

            except OSError:
                pass

        overwrite_and_delete_file(self.__secret_pipe_ssh_key)
        overwrite_and_delete_file(self.__secret_pipe_connect_pass)
        overwrite_and_delete_file(self.__secret_pipe_become_pass)
        overwrite_and_delete_file(self._ssh_known_hosts_file)
        if self.config.run_dir is None:
            rmtree(self._path_run)

        self.__cleaned_up = True

    def __del__(self):
        self.cleanup()
