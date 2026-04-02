from os import environ
from pathlib import Path
from tempfile import mkdtemp
from json import dumps as json_dumps
from shutil import chown
from shutil import which as find_executable

from config import CONTAINER_ENGINES
from utils.filesystem import write_file_with_mode


class ConfigError(ValueError):
    pass


class SetupError(ConfigError):
    pass


class Config:
    # pylint: disable=R0902,R0913,R0917,R0914
    def __init__(
            self,
            playbook_file: str,
            inventory_files: (str, list[str]) = None,
            playbook_dir: str = None,

            limit: (str, list[str]) = None,
            host_pattern: str = None,

            tags: (str, list[str]) = None,
            skip_tags: (str, list[str]) = None,

            extra_vars: dict = None,
            env_vars: dict = None,

            connect_user: str = None,
            connect_pass_file: (str, Path) = None,
            connect_pass_value: str = None,
            become_user: str = None,
            become_pass_file: (str, Path) = None,
            become_pass_value: str = None,
            ssh_key_file: (str, Path) = None,
            ssh_key_value: str = None,

            verbosity: str = None,

            containerized: bool = True,
            container_engine: str = None,
            container_image: str = None,
            timeout_sec_run: int = 3600,
            timeout_sec_start: int = 300,
            run_dir: (str, Path) = None,
            log_stdout_file: (str, Path) = None,
            log_stderr_file: (str, Path) = None,
            log_file_mode: int = 0o640,
            log_file_owner_group: (str, int) = None,
    ):
        self.playbook_file = playbook_file
        self.inventory_files = self._build_list(inventory_files)
        self.playbook_dir: Path = self._build_playbook_dir(playbook_dir)

        self.limit: str = self._build_csv(limit)
        self.host_pattern = host_pattern

        self.tags = self._build_csv(tags)
        self.skip_tags = self._build_csv(skip_tags)

        self.extra_vars = extra_vars
        self.env_vars = env_vars

        self.connect_user = connect_user
        self._connect_pass = self._build_pass(
            which_pass='connect_pass',
            pass_value=connect_pass_value,
            pass_file=connect_pass_file,
        )
        self.become_user = become_user
        self._become_pass = self._build_pass(
            which_pass='become_pass',
            pass_value=become_pass_value,
            pass_file=become_pass_file,
        )
        self._ssh_key = self._build_pass(
            which_pass='ssh_key',
            pass_value=ssh_key_value,
            pass_file=ssh_key_file,
        )

        self.verbosity = verbosity

        self.containerized = containerized
        self.container_engine = self._build_container_engine(
            containerized=containerized,
            engine=container_engine,
        )
        self.container_image = container_image
        self.timeout_sec_run = timeout_sec_run
        self.timeout_sec_start = timeout_sec_start
        self.run_dir = self._build_run_dir(run_dir)
        self.log_stdout_file = self._build_log_file(
            which_log='stdout',
            run_dir=self.run_dir,
            file=log_stdout_file,
            mode=log_file_mode,
            group=log_file_owner_group,
        )
        self.log_stderr_file = self._build_log_file(
            which_log='stderr',
            run_dir=self.run_dir,
            file=log_stderr_file,
            mode=log_file_mode,
            group=log_file_owner_group,
        )

        self._validate()

    @staticmethod
    def _build_playbook_dir(playbook_dir: (str, None)) -> Path:
        if playbook_dir is None:
            playbook_dir = environ.get('HOME', '')

        return Path(playbook_dir)

    @staticmethod
    def _build_list(value: (str, list[str], None)) -> (list[str], None):
        if value is None or not isinstance(value, (str, list)):
            return None

        if isinstance(value, str):
            value = value.strip()
            if len(value) == 0:
                return None

            value = [value]

        if len(value) == 0:
            return None

        return value

    @staticmethod
    def _build_csv(value: (str, list[str], None)) -> (str, None):
        if value is None or not isinstance(value, (str, list)):
            return None

        if isinstance(value, list):
            if len(value) == 0:
                return None

            value = ','.join(value)

        value = value.strip()
        if len(value) == 0:
            return None

        return value

    @staticmethod
    def _build_pass(which_pass: str, pass_value: (str, None), pass_file: (str, Path, None)) -> (str, None):
        if pass_value is not None:
            return pass_value

        if pass_file is None:
            return None

        pass_file = Path(pass_file)
        if not pass_file.is_file():
            raise SetupError(f"Provided '{which_pass}_file' should be an existing file! ({pass_file})")

        try:
            with open(pass_file, 'r', encoding='utf-8') as f:
                return f.read().strip()

        except (OSError, PermissionError) as e:
            raise SetupError(f"Provided '{which_pass}_file' could not be loaded: '{e}'")

    @staticmethod
    def _build_container_engine(containerized: bool, engine: (str, None)) -> str:
        if not containerized:
            return CONTAINER_ENGINES[0]

        if engine in CONTAINER_ENGINES:
            if find_executable(engine) is not None:
                return CONTAINER_ENGINES[engine]

        elif engine is None:
            for possible_engine in CONTAINER_ENGINES:
                if find_executable(possible_engine) is not None:
                    return possible_engine

        raise SetupError("No executable for the provided 'container_engine' could be found!")

    @staticmethod
    def _build_run_dir(path: (str, Path, None)) -> Path:
        if path is None:
            return Path(mkdtemp(prefix='ar_'))

        path = Path(path)
        if not path.is_dir():
            raise SetupError(f"Provided 'run_dir' should be an existing directory! ({path})")

        return path

    @staticmethod
    def _build_log_file(
            which_log: str, run_dir: Path, file: (str, Path, None),
            mode: int, group: (str, int, None),
    ) -> Path:
        if file is None:
            file = run_dir / f'{which_log}.log'

        file = Path(file)
        if file.exists():
            raise SetupError(f"Provided 'log_{which_log}_file' should not already exist! ({file})")

        write_file_with_mode(file=file, content='', file_mode=mode)
        if group is not None:
            try:
                chown(path=file, group=group)

            except LookupError:
                raise SetupError("Provided 'log_file_owner_group' does not exist!")

        return file

    def _validate(self):
        # pylint: disable=R0912
        if str(self.playbook_dir) == '':
            raise ConfigError(
                "Unable to find 'playbook_dir'! "
                "Provide an existing directory containing your playbook-files!"
            )

        if not self.playbook_dir.is_dir():
            raise SetupError(f"Provided 'playbook_dir' should be an existing directory! ({self.playbook_dir})")

        if self.playbook_file.startswith('/'):
            path_pb = Path(self.playbook_file)

        else:
            path_pb = self.playbook_dir / self.playbook_file

        if not path_pb.is_file():
            raise SetupError(
                f"Provided 'playbook_file' should be an existing ansible-playbook! "
                f"Maybe 'playbook_dir' needs be changed? ({path_pb})"
            )

        if self.inventory_files is not None:
            for iv in self.inventory_files:
                if iv.startswith('/'):
                    path_iv = Path(iv)

                else:
                    path_iv = self.playbook_dir / iv

                if not path_iv.is_file() and not path_iv.is_dir():
                    raise SetupError(f"Provided 'inventory_files' do not exist! ({path_iv})")

        if self.verbosity not in [None, 'v', 'vv', 'vvv', 'vvvv', 'vvvvv', 'vvvvvv']:
            raise ConfigError(f"Got bad value for 'verbosity': '{self.verbosity}'")

        if self.extra_vars is not None and not isinstance(self.extra_vars, dict):
            raise ConfigError(f"Got bad type for 'extra_vars': '{type(self.extra_vars)}' (should be dict)")

        if self.env_vars is not None and not isinstance(self.env_vars, dict):
            raise ConfigError(f"Got bad type for 'env_vars': '{type(self.env_vars)}' (should be dict)")

        if not isinstance(self.timeout_sec_run, int):
            raise ConfigError(f"Got bad type for 'timeout_sec_run': '{type(self.timeout_sec_run)}' (should be int)")

        if not isinstance(self.timeout_sec_start, int):
            raise ConfigError(f"Got bad type for 'timeout_sec_start': '{type(self.timeout_sec_start)}' (should be int)")

        # todo: schema-validation of string-values

    def generate_ansible_command(self) -> list[str]:
        # cleaned-up & simplified version of the official "ansible_runner.RunnerConfig.generate_ansible_command"
        cmd = ['ansible-playbook']

        if self.inventory_files is not None:
            for i in self.inventory_files:
                cmd.extend(['-i', str(i)])

        if self.limit is not None:
            cmd.extend(['--limit', self.limit])

        if self.extra_vars is not None and len(self.extra_vars) > 0:
            extra_vars_list = []
            for k in self.extra_vars:
                extra_vars_list.append(f"\"{k}\":{json_dumps(self.extra_vars[k])}")

            cmd.extend(
                [
                    '-e',
                    f'{{{",".join(extra_vars_list)}}}'
                ]
            )

        if self.verbosity is not None:
            cmd.append(f'-{self.verbosity}')

        if self.tags is not None:
            cmd.extend(['--tags', self.tags])

        if self.skip_tags is not None:
            cmd.extend(['--skip-tags', self.skip_tags])

        cmd.append(str(self.playbook_file))
        return cmd


class Runner:
    def __init__(self, config: Config):
        self.config = config
        self.path_run = mkdtemp(prefix='ar_')

    def run(self):
        print(self.config.generate_ansible_command())
