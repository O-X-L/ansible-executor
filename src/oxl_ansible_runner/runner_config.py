from os import getcwd
from pathlib import Path
from shutil import which as find_executable
from shlex import split as split_shell_args
from grp import getgrnam as find_group_by_name

from utils.debug import log
from exceptions import ConfigError, SetupError
from config import CONTAINER_ENGINES, FALLBACK_CONTAINER_IMAGE


class ExecutionConfig:
    # pylint: disable=R0902,R0903,R0913,R0914,R0917

    """
    Arguments:
        ### ANSIBLE-PLAYBOOK EXECUTION

        playbook_file
            The path to the ansible-playbook to execute - absolute or relative from 'playbook_dir'

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html

        inventory_files:
            One or more ansible-inventories to process.
            Alternatively you might want to use dynamic inventories.

            Ansible docs: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_inventory.html
            See also: https://docs.ansible.com/projects/ansible/latest/inventory_guide/intro_dynamic_inventory.html

        playbook_dir:
            Path to the directory containing your ansible-playbooks.
            By default, the current-working-directory is used.
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
            They are added right before the playbook-file.

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

        ssh_known_hosts_file:
            Path to an existing text-file that contains a known-hosts 'public-key-list' of SSH-servers.
            Using such a file is much safer than setting the ANSIBLE_HOST_KEY_CHECKING env-var!
            Security warning: Make sure the file-mode is restrictive!

        ### RUNNER-SPECIFIC

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
            By default, the image 'oxlorg/ansible-executor' is used.
            If you require additional dependencies to be installed, you should use your own.
            You can also use images that are only available locally on your docker-engine server. (built manually)

            Dockerfile: https://github.com/O-X-L/ansible-runner/blob/latest/docker/Dockerfile_executor

        timeout_sec_run:
            Maximum time in seconds that an ansible-playbook execution is allowed to run.
            By default, 1 hour (3600s) is defined.
            The execution will be aborted after the timeout is reached.

        timeout_sec_start:
            Maximum time in seconds that the pre-start (before the ansible-playbook is started) is allowed to take.

        run_dir:
            Path to an existing runtime-directory that is used to store some temporary data in.
            By default, a temporary directory is created for each execution (via mkdtemp).
            It is recommended to pass an absolute path.

        log_stdout_file:
            Path to a location where the output of ansible-playbook should be logged to.
            This may not be an existing file!
            By default, it is created within the 'run_dir' and has the naming 'ansible_stdout_*.log'

        log_stderr_file:
            Path to a location where the error-output of ansible-playbook should be logged to.
            This may not be an existing file!
            By default, it is created within the 'run_dir' and has the naming 'ansible_stderr_*.log'

        log_file_mode:
            File-mode to set for the log-files.
            One of: 0o600, 0o640, 0o644, 0o660, 0o664
            Security warning: Usage of 0o644 or 0o664 is discouraged as it allows 'other' users to read the logs.

        log_file_owner_group:
            The group that should be set as log-file owner.
            Integer (gid) or string (group-name)

    """
    def __init__(
            self,
            playbook_file: (str, Path),
            inventory_files: ((str, Path), list[str|Path]) = None,
            playbook_dir: (str, Path) = None,

            mode_check: bool = False,
            mode_diff: bool = False,

            limit: (str, list[str]) = None,
            host_pattern: str = None,

            tags: (str, list[str]) = None,
            skip_tags: (str, list[str]) = None,

            extra_vars: dict = None,
            env_vars: dict = None,
            env_vars_strip: list[str] = None,
            cmd_args: (str, list[str]) = None,

            ssh_key_file: (str, Path) = None,
            ssh_key_value: str = None,
            connect_user: str = None,
            connect_pass_file: (str, Path) = None,
            connect_pass_value: str = None,
            become_user: str = None,
            become_pass_file: (str, Path) = None,
            become_pass_value: str = None,
            vault_pass_file: (str, Path) = None,
            vault_pass_value: str = None,
            vault_id: (str, list[str]) = None,

            verbosity: (str, int) = None,

            ssh_known_hosts_file: (str, Path) = None,

            containerized: bool = False,
            container_engine: str = None,
            container_image: str = None,
            timeout_sec_run: int = 60 * 60,  # 1h
            timeout_sec_start: int = 300,  # 5m
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
        self.env_vars_strip = env_vars_strip
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
        self.vault_id = self._build_list(vault_id)

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
            playbook_dir = getcwd()

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

    def validate(self):
        self._validate_playbook_dir()
        self._validate_playbook_file()
        self._validate_inventory_files()
        self._validate_run_dir()
        self._validate_ssh_known_hosts_file()
        self._validate_verbosity()
        self._validate_bools()
        self._validate_dicts()
        self._validate_lists()
        self._validate_times()
        self._validate_log_file_settings()
        self._validate_cmd_args()

        # todo: schema-validation of string-values

    def _validate_playbook_dir(self):
        if str(self.playbook_dir).strip() == '':
            raise ConfigError(
                "Unable to find 'playbook_dir'! "
                "Provide an existing directory containing your playbook-files!"
            )

        self._validate_paths(path=self.playbook_dir, which_var='playbook_dir')

        if not self.playbook_dir.is_dir():
            raise SetupError(f"Provided 'playbook_dir' should be an existing directory! ({self.playbook_dir})")

        if not str(self.playbook_dir).startswith('/'):
            log("It is recommended to use absolute paths for 'playbook_dir'!")

    def _validate_playbook_file(self):
        self._validate_paths(path=self.playbook_file, which_var='playbook_file')

        if str(self.playbook_file).startswith('/'):
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

            if iv.startswith('/'):
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

        if not str(self.run_dir).startswith('/'):
            log("It is recommended to use absolute paths for 'run_dir'!")

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
        for attr in ['mode_check', 'mode_diff', 'containerized']:
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
        for attr in ['timeout_sec_run', 'timeout_sec_start']:
            value = getattr(self, attr)
            if not isinstance(value, int):
                raise ConfigError(f"Got bad type for '{attr}': '{type(value)}' (should be int)")

        # todo: set constants
        if self.timeout_sec_start < 10:
            raise ConfigError(
                f"Provided 'timeout_sec_start' is too low: '{self.timeout_sec_start}' (should be at least 10)",
            )

    def _validate_log_file_settings(self):
        if self.log_file_mode not in [0o600, 0o640, 0o644, 0o660, 0o664]:
            raise ConfigError(
                f"Got bad value for 'log_file_mode': '{self.log_file_mode}' "
                f"(should be one of: 0o600 0o640 0o660 0o644 0o664)",
            )

        if self.log_file_mode in [0o644, 0o664]:
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
