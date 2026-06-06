from os import getuid
from pathlib import Path
from shutil import which as find_executable

from oxl_ansible_executor.utils.debug import log
from oxl_ansible_executor.utils.subps import process
from oxl_ansible_executor.utils.util import get_random_str
from oxl_ansible_executor.utils.subps import Process, ProcessArgs
from oxl_ansible_executor.utils.filesystem import write_file_with_mode
from oxl_ansible_executor.exceptions import ExecutionError
from oxl_ansible_executor.config import CONTAINER_ENGINE_DOCKER, CONTAINER_ENGINE_PODMAN, FALLBACK_CONTAINER_IMAGE

from oxl_ansible_executor.runner_executor_base import ExecutorBase
from oxl_ansible_executor.runner_executor_command import AnsibleCommand, wrap_cmd_in_ssh_agent


class ExecutorContainer(ExecutorBase):
    CONTAINER_ENGINE_NAME = None
    CONTAINER_PATHS = {
        'playbook_dir': '/run/ansible',
        'inventory_files': '/run/ansible_inventory',
        'pipe_ssh_key': f'/run/.{get_random_str(10)}',
        'pipe_connect_pass': f'/run/.{get_random_str(10)}',
        'pipe_become_pass': f'/run/.{get_random_str(10)}',
        'pipe_vault_pass': f'/run/.{get_random_str(10)}',
        'ssh_known_hosts_file': '/run/ssh_known_hosts',
    }

    def _engine_init(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ):
        if self.CONTAINER_ENGINE_NAME is None:
            raise NotImplementedError('CONTAINER_ENGINE_NAME has to be defined!')

        self.engine_executable = self._build_engine_executable()
        self._container_volumes = self._build_container_volumes(
            pipe_ssh_key=pipe_ssh_key,
            pipe_connect_pass=pipe_connect_pass,
            pipe_become_pass=pipe_become_pass,
            pipe_vault_pass=pipe_vault_pass,
        )
        cmd_paths = self._build_paths_inside_container(
            pipe_connect_pass=pipe_connect_pass,
            pipe_become_pass=pipe_become_pass,
            pipe_vault_pass=pipe_vault_pass,
        )
        self._ansible_command_generator = AnsibleCommand(
            config=self.config,
            **cmd_paths,
        )
        self.ansible_command = self._ansible_command_generator.generate()
        self._container_name = f'ansible-executor-{self._run_id}'
        self._env_var_file = self.config.run_dir / '.env'

    def _build_engine_executable(self) -> str:
        executable = find_executable(self.CONTAINER_ENGINE_NAME)
        if executable is not None:
            return executable

        return self.CONTAINER_ENGINE_NAME

    # pylint: disable=R0912
    def _build_container_volumes(
            self,
            pipe_ssh_key: Path = None,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    ) -> dict:
        volumes = {
            str(self.config.playbook_dir): self.CONTAINER_PATHS['playbook_dir'],
        }

        if self.config.debug:
            log('Volume mapping:')

        # if inventory-files not inside playbook-dir - we need to mount them
        if self.config.inventory_files is not None:
            for i, iv in enumerate(self.config.inventory_files):
                iv_str = str(iv)
                if iv_str.startswith('/'):
                    iv_inside = Path(self.CONTAINER_PATHS['inventory_files']) / str(i)
                    volumes[iv_str] = str(iv_inside)
                    if self.config.debug:
                        log(f"  {iv_str} => {iv_inside} (inventory)")

        if pipe_ssh_key is not None:
            volumes[str(pipe_ssh_key)] = f"{self.CONTAINER_PATHS['pipe_ssh_key']}:ro"
            if self.config.debug:
                log(f"  {pipe_ssh_key} => {self.CONTAINER_PATHS['pipe_ssh_key']} (ssh-key)")

        if pipe_connect_pass is not None:
            volumes[str(pipe_connect_pass)] = f"{self.CONTAINER_PATHS['pipe_connect_pass']}:ro"
            if self.config.debug:
                log(f"  {pipe_connect_pass} => {self.CONTAINER_PATHS['pipe_connect_pass']} (connect-pass)")

        if pipe_become_pass is not None:
            volumes[str(pipe_become_pass)] = f"{self.CONTAINER_PATHS['pipe_become_pass']}:ro"
            if self.config.debug:
                log(f"  {pipe_become_pass} => {self.CONTAINER_PATHS['pipe_become_pass']} (become-pass)")

        if pipe_vault_pass is not None:
            volumes[str(pipe_vault_pass)] = f"{self.CONTAINER_PATHS['pipe_vault_pass']}:ro"
            if self.config.debug:
                log(f"  {pipe_vault_pass} => {self.CONTAINER_PATHS['pipe_vault_pass']} (vault-pass)")

        if self.config.ssh_known_hosts_file is not None:
            ssh_kh_str = str(self.config.ssh_known_hosts_file)
            volumes[ssh_kh_str] = f"{self.CONTAINER_PATHS['ssh_known_hosts_file']}:ro"
            if self.config.debug:
                log(
                    f"  {self.config.ssh_known_hosts_file} => {self.CONTAINER_PATHS['ssh_known_hosts_file']} "
                    "(ssh-known-hosts)"
                )

        for path_host, path_container in self.config.container_volumes.items():
            volumes[str(path_host)] = str(path_container)

        return volumes

    def _build_paths_inside_container(
            self,
            pipe_connect_pass: Path = None,
            pipe_become_pass: Path = None,
            pipe_vault_pass: Path = None,
    )-> dict:
        paths = {
            'pipe_connect_pass': None,
            'pipe_become_pass': None,
            'pipe_vault_pass': None,
            'inventory_files': [],
            'ssh_known_hosts_file': None,
        }

        if self.config.inventory_files is not None:
            for iv in self.config.inventory_files:
                iv_str = str(iv)
                if iv_str in self._container_volumes:
                    paths['inventory_files'].append(self._container_volumes[iv_str])

                else:
                    paths['inventory_files'].append(iv)

        if pipe_connect_pass is not None:
            paths['pipe_connect_pass'] = self.CONTAINER_PATHS['pipe_connect_pass']

        if pipe_become_pass is not None:
            paths['pipe_become_pass'] = self.CONTAINER_PATHS['pipe_become_pass']

        if pipe_vault_pass is not None:
            paths['pipe_vault_pass'] = self.CONTAINER_PATHS['pipe_vault_pass']

        if self.config.ssh_known_hosts_file is not None:
            paths['ssh_known_hosts_file'] = self.CONTAINER_PATHS['ssh_known_hosts_file']

        return paths

    def _prepare_engine(self):
        self._prepare_container_image()
        self._write_env_var_file()

    def _prepare_container_image(self):
        image_query = process(
            cmd=[self.engine_executable, 'images', '-q', self.config.container_image],
            timeout_sec=5,
            file_stderr=self.config.log_stderr_file,
        )
        configured_image_exists = image_query.stdout is not None

        if self.config.container_image == FALLBACK_CONTAINER_IMAGE:
            if not configured_image_exists:
                self._build_container_image_fallback()

            return

        self._pull_container_image(configured_image_exists)

    def _pull_container_image(self, configured_image_exists: bool):
        if configured_image_exists and not self.config.container_image_pull:
            # optional update
            return

        if self.config.debug:
            log(f'Pulling container-image: {self.config.container_image}')

        image_pull = process(
            cmd=[self.engine_executable, 'image', 'pull', self.config.container_image],
            timeout_sec=self.config.timeout_container_image_pull_build,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )
        if not image_pull.failed:
            return

        msg = f"Failed to pull container image: '{self.config.container_image}'"

        # only fail if the image does not exist and could not be pulled
        if not configured_image_exists:
            raise ExecutionError(msg)

        if self.config.debug:
            log(msg)

    def _build_container_image_fallback(self):
        if self.config.debug:
            log('Building fallback container-image')

        path_dockerfile = Path(__file__).parent / 'container'

        cmd = [
            self.engine_executable,
            'build',
            '-f=Dockerfile_fallback',
            '-t',
            FALLBACK_CONTAINER_IMAGE,
            '--network=host',
            '--no-cache',
            '--build-arg',
            f'AR_UID={getuid()}',
            '.',
        ]
        if self.config.debug:
            log(f'Build command: {cmd}')

        image_build = process(
            cmd=cmd,
            cwd=path_dockerfile,
            timeout_sec=self.config.timeout_container_image_pull_build,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )

        if image_build.failed:
            raise ExecutionError(
                f"Failed to build fallback container-image: '{FALLBACK_CONTAINER_IMAGE}' => {image_build.stderr}"
            )

    def _write_env_var_file(self):
        if self.config.env_vars is None or len(self.config.env_vars) == 0:
            # pylint: disable=W0201
            self._env_var_file = None
            return

        env_var_lines = []
        for key, value in self.config.env_vars.items():
            key = key.replace('=', '')
            env_var_lines.append(f"{key}={value}")

        write_file_with_mode(
            self._env_var_file,
            content='\n'.join(env_var_lines),
            file_mode=0o600,
        )

    def _generate_container_args_volumes(self) -> list[str]:
        args = []
        for path_host, path_container in self._container_volumes.items():
            if str(path_container).find(':') == -1:
                path_container = f'{path_container}:{self.config.container_volume_options}'

            args.extend([
                '-v',
                f"{path_host}:{path_container}",
            ])

        return args

    def _generate_container_args_network(self) -> list[str]:
        if self.config.container_network is None:
            return ['--network=host']

        return [
            '--network',
            self.config.container_network,
        ]

    def generate_engine_command(self) -> list[str]:
        cmd = [
            self.engine_executable,
            'run',
            '--rm',
            '--name', self._container_name,
            '-w', self.CONTAINER_PATHS['playbook_dir'],
        ]
        cmd.extend(self._generate_container_args_volumes())
        cmd.extend(self._generate_container_args_network())

        if self.config.container_engine == CONTAINER_ENGINE_PODMAN:
            cmd.append('--userns=keep-id')

        if self._env_var_file is not None:
            cmd.extend(['--env-file', str(self._env_var_file)])

        cmd.append(self.config.container_image)

        inside_cmd = self.ansible_command.copy()
        # pylint: disable=W0212
        if self.config._ssh_key is not None:
            inside_cmd = wrap_cmd_in_ssh_agent(cmd=inside_cmd, ssh_key_file=self.CONTAINER_PATHS['pipe_ssh_key'])

        cmd.extend(inside_cmd)

        return cmd

    def _create_process(self, cmd: list[str]):
        process_args = ProcessArgs(
            cwd=self.config.run_dir,
            timeout_sec=self.config.timeout_sec_run,
            env=None,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )
        self.process = Process(cmd=cmd, args=process_args)

    def _send_signal_to_ansible(self, signal: int):
        cmd = [
            self.engine_executable,
            'kill',
            '--signal',
            str(signal),
            self._container_name,
        ]
        process(
            cmd=cmd,
            timeout_sec=5,
            file_stdout=self.config.log_stdout_file,
            file_stderr=self.config.log_stderr_file,
        )


class ExecutorContainerDocker(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_DOCKER


class ExecutorContainerPodman(ExecutorContainer):
    CONTAINER_ENGINE_NAME = CONTAINER_ENGINE_PODMAN
