from os import environ
from pathlib import Path
from shutil import which as find_executable
from shlex import split as split_shell_args

from exceptions import ConfigError, SetupError
from config import CONTAINER_ENGINES, FALLBACK_CONTAINER_IMAGE


class ExecutionConfig:
    # pylint: disable=R0902,R0913,R0917,R0914
    def __init__(
            self,
            playbook_file: str,
            inventory_files: (str, list[str]) = None,
            playbook_dir: str = None,

            mode_check: bool = False,
            mode_diff: bool = False,

            limit: (str, list[str]) = None,
            host_pattern: str = None,

            tags: (str, list[str]) = None,
            skip_tags: (str, list[str]) = None,

            extra_vars: dict = None,
            env_vars: dict = None,
            cmd_args: (str, list[str]) = None,

            connect_user: str = None,
            connect_pass_file: (str, Path) = None,
            connect_pass_value: str = None,
            become_user: str = None,
            become_pass_file: (str, Path) = None,
            become_pass_value: str = None,
            ssh_key_file: (str, Path) = None,
            ssh_key_value: str = None,
            vault_pass_file: (str, Path) = None,
            vault_pass_value: str = None,

            verbosity: (str, int) = None,

            ssh_known_hosts_file: (str, Path) = None,

            containerized: bool = False,
            container_engine: str = None,
            container_image: str = None,
            timeout_sec_run: int = 3600,
            timeout_sec_start: int = 300,
            start_pipe_block_sec: int = 10,
            run_dir: (str, Path) = None,
            log_stdout_file: (str, Path) = None,
            log_stderr_file: (str, Path) = None,
            log_file_mode: int = 0o640,
            log_file_owner_group: (str, int) = None,
    ):
        self.playbook_file = playbook_file
        self.inventory_files = self._build_list(inventory_files)
        self.playbook_dir: Path = self._build_playbook_dir(playbook_dir)
        self.run_dir = run_dir

        self.mode_check = mode_check
        self.mode_diff = mode_diff

        self.limit: str = self._build_csv(limit)
        self.host_pattern = host_pattern

        self.tags = self._build_csv(tags)
        self.skip_tags = self._build_csv(skip_tags)

        self.extra_vars = extra_vars
        self.env_vars = env_vars
        self.cmd_args = self._build_cmd_args(cmd_args)

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
        self._vault_pass = self._build_pass(
            which_pass='vault_pass',
            pass_value=vault_pass_value,
            pass_file=vault_pass_file,
        )

        self.verbosity = verbosity

        self.ssh_known_hosts_file = ssh_known_hosts_file

        self.containerized = containerized
        self.container_engine = self._build_container_engine(
            containerized=containerized,
            engine=container_engine,
        )
        self.container_image = self._build_container_image(container_image)
        self.timeout_sec_run = timeout_sec_run
        self.timeout_sec_start = timeout_sec_start
        self.start_pipe_block_sec = start_pipe_block_sec

        self.log_file_mode = log_file_mode
        self.log_file_owner_group = log_file_owner_group
        self.log_stdout_file = self._build_log_file(
            which_log='stdout',
            file=log_stdout_file,
        )
        self.log_stderr_file = self._build_log_file(
            which_log='stderr',
            file=log_stderr_file,
        )

        self.validate()

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
    def _build_container_image(image: (str, None)) -> str:
        if image is None:
            return FALLBACK_CONTAINER_IMAGE

        if image.find(':') == -1:
            return f'{image}:latest'

        return image

    @staticmethod
    def _build_log_file(which_log: str, file: (str, Path, None)) -> (Path, None):
        if file is None:
            return None

        file = Path(file)
        if file.exists():
            raise SetupError(f"Provided 'log_{which_log}_file' should not already exist! ({file})")

        return file

    @staticmethod
    def _build_cmd_args(cmd_args: (str, list[str], None)) -> (list[str], None):
        if cmd_args is None:
            return None

        if isinstance(cmd_args, str):
            cmd_args = split_shell_args(cmd_args)

        if len(cmd_args) == 0:
            return None

        return cmd_args

    def validate(self):
        self._validate_playbook_dir()
        self._validate_playbook_file()
        self._validate_inventory_files()
        self._validate_run_dir()
        self._validate_ssh_known_hosts_file()
        self._validate_verbosity()
        self._validate_bools()
        self._validate_dicts()
        self._validate_times()
        self._validate_log_file_settings()
        self._validate_cmd_args()

        # todo: schema-validation of string-values

    def _validate_playbook_dir(self):
        if str(self.playbook_dir) == '':
            raise ConfigError(
                "Unable to find 'playbook_dir'! "
                "Provide an existing directory containing your playbook-files!"
            )

        if not self.playbook_dir.is_dir():
            raise SetupError(f"Provided 'playbook_dir' should be an existing directory! ({self.playbook_dir})")

    def _validate_playbook_file(self):
        if self.playbook_file.startswith('/'):
            path_pb = Path(self.playbook_file)

        else:
            path_pb = self.playbook_dir / self.playbook_file

        if not path_pb.is_file():
            raise SetupError(
                f"Provided 'playbook_file' should be an existing ansible-playbook! "
                f"Maybe 'playbook_dir' needs be changed? ({path_pb})"
            )

    def _validate_inventory_files(self):
        if self.inventory_files is None:
            return

        for iv in self.inventory_files:
            if iv.startswith('/'):
                path_iv = Path(iv)

            else:
                path_iv = self.playbook_dir / iv

            if not path_iv.is_file() and not path_iv.is_dir():
                raise SetupError(f"Provided 'inventory_files' do not exist! ({path_iv})")

    def _validate_run_dir(self):
        if self.run_dir is None:
            return

        self.run_dir = Path(self.run_dir)

        if not self.run_dir.is_dir():
            raise SetupError(f"Provided 'run_dir' should be an existing directory! ({self.run_dir})")

    def _validate_ssh_known_hosts_file(self):
        if self.ssh_known_hosts_file is None:
            return

        if str(self.ssh_known_hosts_file).startswith('/'):
            self.ssh_known_hosts_file = Path(self.ssh_known_hosts_file)

        else:
            self.ssh_known_hosts_file = self.playbook_dir / self.ssh_known_hosts_file

        if not self.ssh_known_hosts_file.is_file():
            raise SetupError(
                f"Provided 'ssh_known_hosts_file' should be an existing file! "
                f"Maybe 'playbook_dir' needs be changed? ({self.ssh_known_hosts_file})"
            )

    def _validate_verbosity(self):
        if self.verbosity is None:
            return

        if isinstance(self.verbosity, int):
            if self.verbosity < 0 or self.verbosity > 6:
                raise ConfigError(f"Got bad value for 'verbosity': '{self.verbosity}' (0-6 or v-vvvvvv)")

            if self.verbosity == 0:
                self.verbosity = None

            else:
                self.verbosity = 'v' * self.verbosity

            return

        if self.verbosity not in ['v', 'vv', 'vvv', 'vvvv', 'vvvvv', 'vvvvvv']:
            raise ConfigError(f"Got bad value for 'verbosity': '{self.verbosity}' (0-6 or v-vvvvvv)")

    def _validate_bools(self):
        for attr in ['mode_check', 'mode_diff', 'containerized']:
            value = getattr(self, attr)
            if not isinstance(value, bool):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be bool)")

    def _validate_dicts(self):
        for attr in ['extra_vars', 'env_vars']:
            value = getattr(self, attr)
            if value is not None and not isinstance(value, dict):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be dict)")

    def _validate_times(self):
        for attr in ['timeout_sec_run', 'timeout_sec_start', 'start_pipe_block_sec']:
            value = getattr(self, attr)
            if not isinstance(value, int):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be int)")

        if self.start_pipe_block_sec < 5:
            raise ConfigError(
                f"Provided 'start_pipe_block_sec' is too low: '{self.start_pipe_block_sec}' (should be at least 5)",
            )

    def _validate_log_file_settings(self):
        if self.log_file_mode not in [0o600, 0o640, 0o644]:
            raise ConfigError(f"Got bad value for 'log_file_mode': '{self.log_file_mode}'")

        if self.log_file_owner_group is not None and not isinstance(self.log_file_owner_group, (int, str)):
            raise ConfigError(
                f"Got bad type for 'log_file_owner_group': '{type(self.log_file_owner_group)}' (should be int or str)",
            )

    def _validate_cmd_args(self):
        if self.cmd_args is None:
            return

        if not isinstance(self.cmd_args, list):
            raise ConfigError(
                f"Got bad type for 'cmd_args': '{type(self.cmd_args)}' (should be list[str])",
            )

        if len(self.cmd_args) == 0:
            self.cmd_args = None
            return

        if not isinstance(self.cmd_args[0], str):
            raise ConfigError(
                f"Got bad type for 'cmd_args' values: '{type(self.cmd_args)} => {type(self.cmd_args[0])}' "
                f"(should be list[str])",
            )
