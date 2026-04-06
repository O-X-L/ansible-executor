import subprocess
from pathlib import Path
from io import TextIOWrapper
from os import environ, getcwd
from json import dumps as json_dumps


# pylint: disable=R0913,R0917
class ProcessArgs:
    def __init__(
            self,
            shell: bool = False,
            timeout_sec: int = None,
            timeout_shell: bool = True,
            cwd: (Path, str) = None,
            env: dict = None,
            env_inherit: bool = False,
            env_remove: list[str] = None,
            empty_none: bool = True,
            stdin: str = None,
            file_stdout: (str, Path) = None,
            file_stderr: (str, Path) = None,
    ):
        self.shell: bool = shell
        self.timeout_sec: (int, None) = timeout_sec
        self.timeout_shell: (int, None) = timeout_shell
        self.cwd: (Path, str, None) = cwd
        self.env: (dict, None) = env  # specific env-vars to set for the subprocess
        self.env_inherit: bool = env_inherit  # if the subprocess should inherit all env-vars from its parent
        self.env_remove: (list[str], None) = env_remove  # in some cases you might want to strip some env-vars
        self.empty_none: bool = empty_none  # if stdout/stderr is empty-string - return None instead
        self.stdin: (str, None) = stdin
        self.file_stdout: (Path, str, None) = file_stdout  # file to pipe/log the stdout to
        self.file_stderr: (Path, str, None) = file_stderr  # file to pipe/log the stderr to


class ProcessResult:
    def __init__(self, stdout: (str, None), stderr: (str, None), rc: int, pid: int, empty_none: bool = True):
        self._stdout: (str, None) = stdout
        self._stderr: (str, None) = stderr
        self.rc: int = rc
        self.pid: int = pid
        self.empty_none: bool = empty_none
        self.process_error: bool = False

    @property
    def stdout(self) -> (str, None):
        if self._stdout is None:
            if self.empty_none:
                return None

            return ''

        if self._stdout.strip() == '' and self.empty_none:
            return None

        return self._stdout

    @stdout.setter
    def stdout(self, value: str):
        self._stdout = value

    def stdout_append(self, value: str):
        if self._stdout is None:
            self._stdout = value

        self._stdout += value

    @property
    def stdout_lines(self) -> list[str]:
        if self.stdout is None:
            return []

        return self.stdout.split('\n')

    @property
    def stderr(self) -> (str, None):
        if self._stderr is None:
            if self.empty_none:
                return None

            return ''

        if self._stderr.strip() == '' and self.empty_none:
            return None

        return self._stderr

    @stderr.setter
    def stderr(self, value: str):
        self._stderr = value

    def stderr_append(self, value: str):
        if self._stderr is None:
            self._stderr = value

        self._stderr += value

    @property
    def stderr_lines(self) -> list[str]:
        if self.stderr is None:
            return []

        return self.stderr.split('\n')

    @property
    def failed(self) -> bool:
        if self.rc == -1:
            return False

        return self.rc != 0

    def to_dict(self) -> dict:
        return {
            'failed': self.failed,
            'rc': self.rc,
            'pid': self.pid if self.pid != -1 else None,
            'stdout': self.stdout,
            'stderr': self.stderr,
            'stdout_lines': self.stdout_lines,
            'stderr_lines': self.stderr_lines,
        }

    # pylint: disable=R0801
    def to_json(self, pretty: bool = False) -> str:
        indent = 0
        if pretty:
            indent = 2

        return json_dumps(self.to_dict(), default=str, indent=indent)

    def __repr__(self) -> str:
        return self.to_json(pretty=True)


class Process:
    def __init__(self, cmd: (str, list[str]), args: ProcessArgs = None):
        if args is None:
            args = ProcessArgs()

        self.args = args
        self._result = ProcessResult(stdout='', stderr='', rc=-1, pid=-1, empty_none=args.empty_none)
        self.env = self._prep_env(args)
        self.cwd = self._build_cwd(args.cwd)
        self.cmd = self._build_command(cmd)

        self.p = None
        self._started = False
        self._closed = False
        self._log_files_loaded = False
        self._pipe_stdout = None
        self._pipe_stderr = None

    @property
    def finished(self) -> bool:
        if self._closed and self._result.rc != -1:
            return True

        if self.p is None:
            return False

        try:
            self.p.poll()
            return self.p.returncode is not None

        except AttributeError:
            # self.p got closed/nulled-out meanwhile
            return self._closed and self._result.rc != -1

    @property
    def result(self) -> ProcessResult:
        if not self.finished:
            return self._result

        self._update_result()
        return self._result

    def _update_result(self):
        if self._result.rc == -1:
            self._result.rc = self.p.returncode

        self._load_stdout_stderr_from_logfiles()

    def wait_until_finished(self) -> ProcessResult:
        if not self._started:
            self.start()

        try:
            communicate_kwargs = {'timeout': self.args.timeout_sec}
            if self.args.stdin is not None:
                communicate_kwargs['input'] = self.args.stdin.encode('utf-8')

            b_stdout, b_stderr = self.p.communicate(**communicate_kwargs)

            self._result.rc = self.p.returncode

            if self.args.file_stdout is None:
                self._result.stdout = b_stdout.decode('utf-8').strip()

            if self.args.file_stderr is None:
                self._result.stderr = b_stderr.decode('utf-8').strip()

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, subprocess.CalledProcessError,
                OSError, IOError, FileNotFoundError) as error:
            self._log_process_error(error)

        return self.result

    def start(self) -> subprocess.Popen:
        if self._started:
            raise ValueError('Process cannot be started again!')

        self._pipe_stdout = self._prep_output_pipe(self.args.file_stdout)
        self._pipe_stderr = self._prep_output_pipe(self.args.file_stderr)
        try:
            self._started = True

            # pylint: disable=R1732
            self.p = subprocess.Popen(
                self.cmd,
                shell=self.args.shell,
                stdout=self._pipe_stdout,
                stderr=self._pipe_stderr,
                stdin=subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
            )

            return self.p

        except (subprocess.SubprocessError, subprocess.CalledProcessError, OSError, IOError,
                FileNotFoundError) as error:
            self._log_process_error(error)
            raise

    def send_signal(self, signal: int):
        if self.p is None:
            return

        self.p.send_signal(signal)

    def __enter__(self) -> subprocess.Popen:
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self._update_result()
        self._closed = True
        self.p = None
        if self._pipe_stdout:
            self._pipe_stdout.close()

        if self._pipe_stderr:
            self._pipe_stderr.close()

    def _log_process_error(self, error):
        self._result.process_error = True
        stderr = str(error)
        self._result.stderr_append(stderr)
        self._result.rc = 1

        if self.args.file_stderr is not None:
            with open(self.args.file_stderr, 'a', encoding='utf-8') as f:
                f.write('\n' + stderr + '\n')

    def _load_stdout_stderr_from_logfiles(self):
        if self._log_files_loaded:
            return

        self._log_files_loaded = True
        if self.args.file_stdout is not None:
            if self._result.stdout is None:
                self._result.stdout = ''

            with open(self.args.file_stdout, 'r', encoding='utf-8') as f:
                self._result.stdout_append(f.read().strip())

        if self.args.file_stderr is not None:
            if self._result.stderr is None:
                self._result.stderr = ''

            with open(self.args.file_stderr, 'r', encoding='utf-8') as f:
                self._result.stderr_append(f.read().strip())

    @staticmethod
    def _build_cwd(cwd: (str, Path, None)) -> (str, Path):
        if cwd is not None:
            return cwd

        return getcwd()

    def _build_command(self, cmd: (str, list[str])) -> (str, list[str]):
        if isinstance(cmd, list):
            cmd_str = ' '.join(cmd)

        else:
            cmd_str = cmd

        if self.args.shell:
            cmd = cmd_str
            if self.args.timeout_shell and self.args.timeout_sec is not None:
                cmd = f'timeout {self.args.timeout_sec} {cmd}'

        elif not isinstance(cmd, list):
            cmd = cmd.split(' ')

        return cmd

    @staticmethod
    def _prep_env(args: ProcessArgs) -> dict:
        env = {}
        if args.env is not None:
            env = args.env.copy()

        if not args.env_inherit:
            return env

        env_remove = []
        if args.env_remove is not None:
            env_remove = args.env_remove.copy()

        # merge provided env with current env
        env = {**environ.copy(), **env}
        for k in env_remove:
            if k in env:
                env.pop(k)

        return env

    @staticmethod
    def _prep_output_pipe(target_file: (str, Path, None)) -> (int, TextIOWrapper):
        if target_file is None:
            return subprocess.PIPE

        file = Path(target_file)
        if not Path(file).is_file():
            raise FileNotFoundError(f"Process output-log-file (pipe) should be an existing file! ({target_file})")

        # pylint: disable=R1732
        pipe = open(file, 'ab')
        return pipe


def process(cmd: (str, list[str]), *args, **kwargs) -> ProcessResult:
    p = Process(cmd=cmd, args=ProcessArgs(*args, **kwargs))
    p.start()
    return p.wait_until_finished()
