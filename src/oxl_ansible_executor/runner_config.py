from os import getcwd
from pathlib import Path
from shutil import which as find_executable
from shlex import split as split_shell_args
from grp import getgrnam as find_group_by_name

from utils.debug import log
from exceptions import ConfigError, SetupError
from config import CONTAINER_ENGINES, FALLBACK_CONTAINER_IMAGE


class ExecutionConfig:
    # pylint: disable=R0902,R0913,R0914,R0917

    """
    Arguments:
        ### ANSIBLE-PLAYBOOK EXECUTION

        playbook_file
            The path to the ansible-playbook to execute - absolute or relative pointing to inside 'playbook_dir'

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html

        inventory_files:
            One or more ansible-inventories to process.
            Alternatively you might want to use dynamic inventories.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html
            See also: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_dynamic_inventory.html

        playbook_dir:
            Path to the directory containing your ansible-playbooks.
            Defaults:
                If the playbook_file is an absolute path - its parent-directory is used.
                As fallback the current-working-directory is used.
            It is recommended to pass an absolute path.

        mode_check:
            Make ansible-modules run in check/dry-run mode.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html

        mode_diff:
            Make ansible show differences in the output.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html

        limit:
            Limit the targeted inventory-hosts by inventory-hostname or -groups.
            List of hosts/groups (recommended) or comma-separated string.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_patterns.html

        host_pattern:
            Limit the targeted inventory-hosts by a pattern.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_patterns.html

        tags:
            Only run ansible-tasks that have these tags set.
            List of tag-strings (recommended) or comma-separated string.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_tags.html

        skip_tags:
            Skip all ansible-tasks that have these tags set.
            List of tag-strings (recommended) or comma-separated string.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_tags.html

        extra_vars:
            Extra ansible variables to define at execution.
            Security warning: Be aware that these are added to the CLI-args and thus their values can be seen in the
                process-list!

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_variables.html

        env_vars:
            Environmental-variables to define for the ansible execution.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/env_lookup.html

        env_vars_strip:
            Only relevant for local executors.
            As a local executor inherits the environmental-variables of the runner-process, there may be situations
                where have to strip/hide some of them. (p.e. secret values)
            List of env-var-names to strip.

        cmd_args:
            List of arguments or simple string (string is not recommended).
            Usage of it is discouraged! It may lead to unexpected behavior!
            Most use-cases may better be addressed by configuring ansible.cfg settings or
                even variables inside the playbook!
            Additional commandline-arguments to pass to the ansible-playbook execution.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/cli/ansible-playbook.html
            Ansible config docs: https://docs.ansible.com/projects/ansible/latest/reference_appendices/config.html
            Subprocess docs: https://docs.python.org/3/library/subprocess.html#subprocess.Popen

        ssh_key_file:
            Path to an existing unencrypted SSH-private-key required to connect to the target-system.
            Security warning: Make sure the file-mode is restrictive!
            Security hint: If you are using the non-containerized executor,
                you can also load the SSH-key into an SSH-agent beforehand.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/connection_details.html#setting-up-ssh-keys

        ssh_key_value:
            Directly pass the unencrypted SSH-private-key required to connect to the target-system.
            Security hint: If you are using the non-containerized executor,
                you can also load the SSH-key into an SSH-agent beforehand.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/connection_details.html#setting-up-ssh-keys

        connect_user:
            Username that ansible should use to connect to the target-system.

        connect_pass_file:
            Path to an existing text-file that contains the password required to connect to the target-system.
            Security warning: Make sure the file-mode is restrictive!

        connect_pass_value:
            Directly pass the password required to connect to the target-system.

        become_user:
            Username that ansible should use to escalate its privileges on the target-system.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_privilege_escalation.html

        become_pass_file:
            Path to an existing text-file that contains the password required to escalate ansible's privileges
                on the target-system.
            Security warning: Make sure the file-mode is restrictive!

        become_pass_value:
            Directly pass the password required to escalate ansible's privileges on the target-system.

        vault_pass_file:
            Path to an existing text-file that contains the password required to decrypt ansible-vault's.
            Security warning: Make sure the file-mode is restrictive!

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html

        vault_pass_value:
            Directly pass the password required to decrypt ansible-vault's.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html

        vault_id:
            One or more vault-ID's to pass to the execution.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/vault_guide/index.html

        verbosity:
            Can be used to increase the amount of context-information ansible shows in its output.
            Integer between 0-6 or CLI-like string 'v-vvvvvv'

        output_color:
            Whether the ansible-output should be colored.

        ssh_known_hosts_file:
            Path to an existing text-file that contains a known-hosts 'public-key-list' of SSH-servers.
            Using such a file is much safer than setting the ANSIBLE_HOST_KEY_CHECKING env-var!
            Security warning: Make sure the file-mode is restrictive!

        ### RUNNER-SPECIFIC

        debug:
            Whether the executor should print some debug-output to stdout.

        stats_live:
            Requires the 'oxl-ansible-executor-plugins' to be installed inside the execution venv/container!
            Whether the executor should fetch ansible-stats in realtime (every 10s) while ansible executes to populate
            'ExecutionStatus.stats*'. This can be useful if you have long-running playbooks and want to react to
            failures etc.

        stats_recap:
            Requires the 'oxl-ansible-executor-plugins' to be installed inside the execution venv/container!
            Whether the executor should fetch ansible-stats at the end of ansible executions to populate
            'ExecutionStatus.stats*'.

        containerized:
            Whether to execute ansible inside a container.
            It has security benefits to do so.
            Note: The local SSH-agent is not available inside a container.

        container_engine:
            What container-engine to use.
            Either: docker or podman
            You can modify the docker-CLI config-file beforehand to p.e. set a remote docker-engine server as target.

            Docker config docs: https://docs.docker.com/reference/cli/docker/#configuration-files

        container_image:
            Container-image to run ansible in.
            By default, a minimal local container-image is built. (localhost/ansible-executor:${UID})
            If you require additional dependencies to be installed, you should use your own.
            You can also use images that are only available locally on your docker-engine server. (built manually)

            Dockerfile: https://github.com/O-X-L/ansible-executor/blob/latest/docker/Dockerfile_executor

        container_image_pull:
            With this option enabled, the executor will check-for & pull your configured image every time before
                executing.
            If this option is disabled - it will only be pulled if it does not already exist.
            This option is ignored if the default/fallback image is used.

        container_network:
            Optionally set the container-engine-network that should be used for the ansible-executor container.
            See: '--network' container-engine-option

        timeout_sec_run:
            Maximum time in seconds that an ansible-playbook execution is allowed to run.
            By default, 1 hour (3600s) is defined.
            The execution will be aborted after the timeout is reached.

        timeout_sec_start:
            Maximum time in seconds that the pre-start (before the ansible-playbook is started) is allowed to take.

        timeout_container_image_pull_build:
            Maximum time a container-image pull or build (fallback-image only) is allowed to take.

        run_dir:
            Path to an existing runtime-directory that is used to store some temporary data in.
            By default, a temporary directory is created for each execution (via mkdtemp).
            It is recommended to pass an absolute path.

        log_stdout_file:
            Path to a location where the output of ansible-playbook should be logged to.
            This may not be an existing file!
            By default, it is created within the 'run_dir' and has the naming 'ansible_*_stdout.log'

        log_stderr_file:
            Path to a location where the error-output of ansible-playbook should be logged to.
            This may not be an existing file!
            By default, it is created within the 'run_dir' and has the naming 'ansible_*_stderr.log'

        log_file_mode:
            File-mode to set for the log-files.
            One of: 0o600, 0o640, 0o644, 0o660, 0o664
            Security warning: Usage of 0o644 or 0o664 is discouraged as it allows 'other' users to read the logs.

        log_file_owner_group:
            The group that should be set as log-file owner.
            Integer (gid) or string (group-name)

        load_log_stdout:
            Whether the output of the ansible-process should be loaded from the log-file when the execution finished to
            populate "ExecutionStatus.stdout". Depending on your ansible-playbook and -inventory this
            might require 'much' memory.

        load_log_stderr:
            Whether the error-output of the ansible-process should be loaded from the log-file when the execution
            finished to populate "ExecutionStatus.stderr".
    """
    def __init__(
            self,
            playbook_file: str|Path,
            inventory_files: str|Path|list[str|Path] = None,
            playbook_dir: str|Path = None,

            mode_check: bool = False,
            mode_diff: bool = False,

            limit: str|list[str] = None,
            host_pattern: str = None,

            tags: str|list[str] = None,
            skip_tags: str|list[str] = None,

            extra_vars: dict = None,
            env_vars: dict = None,
            env_vars_strip: list[str] = None,
            cmd_args: str|list[str] = None,

            ssh_key_file: str|Path = None,
            ssh_key_value: str = None,
            connect_user: str = None,
            connect_pass_file: str|Path = None,
            connect_pass_value: str = None,
            become_user: str = None,
            become_pass_file: str|Path = None,
            become_pass_value: str = None,
            vault_pass_file: str|Path = None,
            vault_pass_value: str = None,
            vault_id: str|list[str] = None,

            verbosity: (str, int) = None,
            output_color: bool = True,

            ssh_known_hosts_file: str|Path = None,

            debug: bool = False,
            stats_live: bool = False,
            stats_recap: bool = True,

            containerized: bool = False,
            container_engine: str = None,
            container_image: str = None,
            container_image_pull: bool = False,
            container_network: str = None,
            timeout_sec_run: int = 60 * 60,
            timeout_sec_start: int = 5 * 60,
            timeout_container_image_pull_build: int = 3 * 60,
            run_dir: str|Path = None,
            log_stdout_file: str|Path = None,
            log_stderr_file: str|Path = None,
            log_file_mode: int = 0o640,
            log_file_owner_group: str|int = None,
            load_log_stdout: bool = False,
            load_log_stderr: bool = False,
    ):
        self.playbook_dir: Path = self._build_playbook_dir(playbook_dir=playbook_dir, playbook_file=playbook_file)
        self.playbook_file: (str, Path) = self._build_playbook_file(playbook_file)
        self.inventory_files: (list[str|Path], None) = self._build_inventory_files(inventory_files)
        self.run_dir: (Path, None) = run_dir

        self.mode_check: bool = mode_check
        self.mode_diff: bool = mode_diff

        self.limit: (str, None) = self._build_csv(limit)
        self.host_pattern: (str, None) = host_pattern

        self.tags: (str, None) = self._build_csv(tags)
        self.skip_tags: (str, None) = self._build_csv(skip_tags)

        self.extra_vars: (dict[str, str], None) = self._build_dict_of_string(extra_vars)
        self.env_vars: (dict[str, str], None) = self._build_dict_of_string(env_vars)
        self.env_vars_strip: (list[str], None) = env_vars_strip
        self.cmd_args: (str, list[str], None) = self._build_cmd_args(cmd_args)

        self.connect_user: (str, None) = connect_user
        self._connect_pass: (str, None) = self._build_pass(
            which_pass='connect_pass',
            pass_value=connect_pass_value,
            pass_file=connect_pass_file,
        )
        self.become_user: (str, None) = become_user
        self._become_pass: (str, None) = self._build_pass(
            which_pass='become_pass',
            pass_value=become_pass_value,
            pass_file=become_pass_file,
        )
        self._ssh_key: (str, None) = self._build_pass(
            which_pass='ssh_key',
            pass_value=ssh_key_value,
            pass_file=ssh_key_file,
        )
        self._vault_pass: (str, None) = self._build_pass(
            which_pass='vault_pass',
            pass_value=vault_pass_value,
            pass_file=vault_pass_file,
        )
        self.vault_id: (list[str], None) = self._build_list(vault_id)

        self.verbosity: (str, int, None) = verbosity
        self.output_color: bool = output_color

        self.ssh_known_hosts_file: (str, Path, None) = ssh_known_hosts_file

        self.debug: bool = debug
        self.stats_live: bool = stats_live
        self.stats_recap: bool = stats_recap
        self.containerized: bool = containerized
        self.container_engine: str = self._build_container_engine(
            containerized=containerized,
            engine=container_engine,
        )
        self.container_image: str = self._build_container_image(container_image)
        self.container_image_pull: bool = container_image_pull
        self.container_network: (str, None) = container_network
        self.timeout_sec_run: int = timeout_sec_run
        self.timeout_sec_start: int = timeout_sec_start
        self.timeout_container_image_pull_build: int = timeout_container_image_pull_build

        self.log_file_mode: int = log_file_mode
        self.log_file_owner_group: (int, str, None) = log_file_owner_group
        self.log_stdout_file: (Path, None) = self._build_log_file(
            which_log='stdout',
            file=log_stdout_file,
        )
        self.log_stderr_file: (Path, None) = self._build_log_file(
            which_log='stderr',
            file=log_stderr_file,
        )
        self.load_log_stdout: bool = load_log_stdout
        self.load_log_stderr: bool = load_log_stderr

        self.validate()

    def validate(self):
        self._validate_playbook_dir()
        self._validate_playbook_file()
        self._validate_inventory_files()
        self._validate_run_dir()
        self._validate_ssh_key_file()
        self._validate_ssh_known_hosts_file()
        self._validate_verbosity()
        self._validate_bools()
        self._validate_dicts()
        self._validate_lists()
        self._validate_times()
        self._validate_log_file_settings()
        self._validate_cmd_args()

        # todo: schema-validation of string-values

    @staticmethod
    def append_to_list(values: (list, None), to_append) -> list:
        if values is None:
            values = []

        values.append(to_append)
        return values

    @staticmethod
    def add_to_dict(values: (dict, None), key: str, value: str) -> dict:
        if values is None:
            values = {}

        values[key] = value
        return values

    def _build_playbook_file(self, playbook_file: (str, Path, None)) -> (Path, None):
        if playbook_file is None:
            return None

        return self._translate_absolute_path_inside_playbook_dir(playbook_file)

    @staticmethod
    def _build_playbook_dir(playbook_dir: (str, Path, None), playbook_file: (str, Path, None)) -> Path:
        if playbook_dir is None:
            if playbook_file is not None and str(playbook_file).startswith('/') and Path(playbook_file).is_file():
                playbook_dir = Path(playbook_file).parent

            else:
                playbook_dir = getcwd()

        return Path(playbook_dir)

    def _build_inventory_files(self, inventory_files) -> (None, list[Path]):
        inventory_files = self._build_list(inventory_files)

        if inventory_files is None:
            return None

        if not isinstance(inventory_files, list):
            # will fail validation
            return inventory_files

        updated_inventory_files = []
        for iv in inventory_files:
            updated_inventory_files.append(
                self._translate_absolute_path_inside_playbook_dir(iv)
            )

        return updated_inventory_files

    def _translate_absolute_path_inside_playbook_dir(self, path: (str, Path)) -> Path:
        # ensure we use relative paths for files/dirs inside the playbook_dir (easier for containerization)
        if not str(path).startswith('/'):
            return path

        if not str(path).startswith(str(self.playbook_dir)):
            return path

        path = str(path).replace(str(self.playbook_dir), '')
        if path.startswith('/'):
            path = path[1:]

        return Path(path)

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
                return f.read()

        except (OSError, PermissionError) as e:
            raise SetupError(f"Provided '{which_pass}_file' could not be loaded: '{e}'")

    @staticmethod
    def _build_container_engine(containerized: bool, engine: (str, None)) -> str:
        if not containerized:
            return CONTAINER_ENGINES[0]

        if engine in CONTAINER_ENGINES:
            if find_executable(engine) is not None:
                return engine

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

        if not isinstance(cmd_args, (str, list)):
            # validation will fail
            return cmd_args

        if isinstance(cmd_args, str):
            cmd_args = split_shell_args(cmd_args)

        if len(cmd_args) == 0:
            return None

        return cmd_args

    @staticmethod
    def _build_dict_of_string(value: (dict, None)) -> (dict[str, str], None):
        if value is None:
            return None

        if not isinstance(value, dict):
            # will fail validation
            return value

        out = {}
        for k, v in value.items():
            out[str(k)] = str(v)

        return out

    def _validate_playbook_dir(self):
        if str(self.playbook_dir).strip() == '':
            raise ConfigError(
                "Unable to find 'playbook_dir'! "
                "Provide an existing directory containing your playbook-files!"
            )

        self._validate_paths(path=self.playbook_dir, which_var='playbook_dir')

        if not self.playbook_dir.is_dir():
            raise SetupError(f"Provided 'playbook_dir' should be an existing directory! ({self.playbook_dir})")

        if not str(self.playbook_dir).startswith('/') and self.debug:
            log("It is recommended to use absolute paths for 'playbook_dir'!")

    def _validate_playbook_file(self):
        self._validate_paths(path=self.playbook_file, which_var='playbook_file')

        if str(self.playbook_file).startswith('/'):
            if not str(self.playbook_file).startswith(str(self.playbook_dir)):
                raise SetupError(
                    f"Provided 'playbook_file' should be placed inside the 'playbook_dir'! "
                    f"({self.playbook_file} not in {self.playbook_dir})"
                )

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
            self._validate_paths(path=iv, which_var='inventory_files')

            if str(iv).startswith('/'):
                path_iv = Path(iv)

            else:
                path_iv = self.playbook_dir / iv

            if not path_iv.is_file() and not path_iv.is_dir():
                raise SetupError(f"Provided 'inventory_files' do not exist! ({path_iv})")

    def _validate_run_dir(self):
        if self.run_dir is None:
            return

        self._validate_paths(path=self.run_dir, which_var='run_dir')

        self.run_dir = Path(self.run_dir)

        if not self.run_dir.is_dir():
            raise SetupError(f"Provided 'run_dir' should be an existing directory! ({self.run_dir})")

        if not str(self.run_dir).startswith('/') and self.debug:
            log("It is recommended to use absolute paths for 'run_dir'!")

    def _validate_ssh_key_file(self):
        if self._ssh_key is None or self.containerized:
            return

        if find_executable('ssh-agent') is None:
            raise SetupError("To use ssh-keys the 'ssh-agent' has to be installed!")

    def _validate_ssh_known_hosts_file(self):
        if self.ssh_known_hosts_file is None:
            return

        self._validate_paths(path=self.ssh_known_hosts_file, which_var='ssh_known_hosts_file')

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
                # note: can only build after validating
                self.verbosity = 'v' * self.verbosity

            return

        if self.verbosity not in ['v', 'vv', 'vvv', 'vvvv', 'vvvvv', 'vvvvvv']:
            raise ConfigError(f"Got bad value for 'verbosity': '{self.verbosity}' (0-6 or v-vvvvvv)")

    @staticmethod
    def _validate_paths(path: (str, Path), which_var: str):
        if not isinstance(path, (str, Path)):
            raise ConfigError(f"Got bad type for '{which_var}' : {type(path)} (should be str or Path)")

    def _validate_bools(self):
        for attr in [
            'mode_check', 'mode_diff', 'containerized', 'output_color', 'debug', 'container_image_pull',
            'stats_live', 'stats_recap', 'load_log_stdout', 'load_log_stderr',
        ]:
            value = getattr(self, attr)
            if not isinstance(value, bool):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be bool)")

    def _validate_dicts(self):
        for attr in ['extra_vars', 'env_vars']:
            value = getattr(self, attr)
            if value is not None and not isinstance(value, dict):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be dict)")

    def _validate_lists(self):
        if self.env_vars_strip is not None and not isinstance(self.env_vars_strip, list):
            raise ConfigError(f"Got bad type for 'env_vars_strip': '{type(self.env_vars_strip)}' (should be list)")

    def _validate_times(self):
        for attr in ['timeout_sec_run', 'timeout_sec_start', 'timeout_container_image_pull_build']:
            value = getattr(self, attr)
            if not isinstance(value, int):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be int)")

        # todo: set constants
        if self.timeout_sec_start < 10:
            raise ConfigError(
                f"Provided 'timeout_sec_start' is too low: '{self.timeout_sec_start}' (should be at least 10)",
            )

        if self.timeout_container_image_pull_build < 30:
            raise ConfigError(
                f"Provided 'timeout_container_image_pull_build' is too low: "
                f"'{self.timeout_container_image_pull_build}' (should be at least 30)",
            )

    def _validate_log_file_settings(self):
        if self.log_file_mode not in [0o600, 0o640, 0o644, 0o660, 0o664]:
            raise ConfigError(
                f"Got bad value for 'log_file_mode': '{self.log_file_mode}' "
                f"(should be one of: 0o600 0o640 0o660 0o644 0o664)",
            )

        if self.log_file_mode in [0o644, 0o664] and self.debug:
            log(
                "Provided 'log_file_mode' allows 'other' users to read the logs - this might be a security issue! "
                "Maybe utilize 'log_file_owner_group' instead?",
            )

        if self.log_file_owner_group is None:
            return

        if not isinstance(self.log_file_owner_group, (int, str)):
            raise ConfigError(
                f"Got bad type for 'log_file_owner_group': '{type(self.log_file_owner_group)}' (should be int or str)",
            )

        if isinstance(self.log_file_owner_group, int) and self.log_file_owner_group < 0:
            raise ConfigError(
                f"Got bad value for 'log_file_owner_group': '{self.log_file_owner_group}' "
                f"(should be gid or group-name)",
            )

        if isinstance(self.log_file_owner_group, str):
            try:
                find_group_by_name(self.log_file_owner_group)

            except KeyError:
                raise ConfigError(f"Provided 'log_file_owner_group' does not exist: '{self.log_file_owner_group}'")

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

        # todo: warn if args with built-in support are used via cmd_args instead
