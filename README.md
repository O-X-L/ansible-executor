# Ansible Runner minimal

<p align="center">
    <a title="Support this Project (Donate, Support-Licenses)" href="https://shop.oxl.app/collections/open-source">
        <img src="https://files.oxl.at/img/badge-oss-support.svg" alt="Support Badge (Donate, Support-Licenses)"/>
    </a>
</p>

----

[![Check Docs](https://github.com/O-X-L/ansible-executor/actions/workflows/check_docs.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-executor/actions/workflows/check_docs.yml)
[![Lint](https://github.com/O-X-L/ansible-executor/actions/workflows/lint.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-executor/actions/workflows/lint.yml)
[![Unit-Tests](https://github.com/O-X-L/ansible-executor/actions/workflows/unit_test.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-executor/actions/workflows/unit_test.yml)
[![Integration-Tests](https://github.com/O-X-L/ansible-executor/actions/workflows/integration_test.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-executor/actions/workflows/integration_test.yml)

**DISCLAIMER**: This is an **unofficial community project**! Do not confuse it with the vanilla [Ansible](https://ansible.com/) product!

**WARNING**: This project is still in early development. DO NOT use it in production!

## Scope

The scope of this project is it to create a simple and transparent Python3-interface that can be used to execute Ansible-playbooks.

It will focus on using docker or podman to execute ansible in an isolated environment. But local execution will also be available.

The implementation will be opinionated and will have a 'narrow' interface.

## Use-Cases

See: Our simple [Ansible WebUI](https://github.com/O-X-L/ansible-webui)

## Roadmap

- [ ] Ansible Execution
  - [x] Config Object & Validation incl. inline-docs
  - [ ] Engines
    - [x] Local Executor
    - [ ] Container Executor
      - [ ] Docker
      - [ ] Podman
  - [ ] Functionality
    - [x] Playbook targeting local machine
    - [ ] Playbook targeting remote Linux server (SSH-Key, Connect-Pass, Become-Pass, Vault-Pass)
      - [x] Pass secrets via one-time-read Pipes/FIFO (*in-memory - does not write to disk*)
    - [x] Stopping job
    - [x] Redirect output (stdout/stderr) to log-files
- [ ] Tests
  - [ ] Unit-Tests for all components (>85% coverage)
    - [ ] Execution Config-Validation
    - [ ]
  - [ ] Integration-Tests for many practical use-cases
    - [x] Simple execution targeting localhost
    - [x] Passing extra-vars
    - [x] Passing env-vars
    - [x] Enabling output-colors
    - [x] User stopping execution
    - [x] Execution reached timeout
    - [ ] Passing secrets
      - [ ] As values
      - [ ] As files
    - [ ] SSH
      - [ ] SSH-Key usage
      - [ ] Known-Hosts file
    - [ ] tbc...
  - [ ] Integration-Tests also for containerized executor

----

## Usage

```python3
from oxl_ansible_executor import Execution, ExecutionConfig

c = ExecutionConfig(
  playbook_dir='/home/abc/ansible/',
  playbook_file='test.yml',
  inventory_files='inv/env1/hosts.yml',
)
e = Execution(c)

e.run(blocking=True)

print(e.status)
# {
#   "finished": true,
#   "playbook_finished": true,
#   "failed": false,
#   "time_start": 1775467217,
#   "time_finish": 1775467218,
#   "time_duration_sec": 1,
#   "log_stdout_file": "/home/abc/.local/share/oxl-ansible-executor/ansible_stdout_1775467217_qroNP.log",
#   "log_stderr_file": "/home/abc/.local/share/oxl-ansible-executor/ansible_stderr_1775467217_qroNP.log",
#   "process_command": [
#     "/home/abc/.venv/bin/ansible-playbook",
#     "play1.yml"
#   ],
#   "process_rc": 0,
#   "process_result": {
#     "failed": false,
#     "rc": 0,
#     "pid": null,
#     "stdout": "PLAY [localhost] ***************************************************************\n\nTASK [test1 : TEST 1 | Basic] **************************************************\nok: [localhost] => {\n    \"msg\": \"TEST 1: 'NOT SET'\"\n}\n\nTASK [test1 : TEST 1 | Checking environmental variable] ************************\nskipping: [localhost]\n\nTASK [test1 : TEST 1 | Showing environmental variable] *************************\nskipping: [localhost]\n\nTASK [test1 : TEST 1 | Sleeping] ***********************************************\nskipping: [localhost]\n\nTASK [test1 : TEST 1 | Fail] ***************************************************\nskipping: [localhost]\n\nPLAY RECAP *********************************************************************\nlocalhost                  : ok=1    changed=0    unreachable=0    failed=0    skipped=4    rescued=0    ignored=0",
#     "stderr": "[WARNING]: No inventory was parsed, only implicit localhost is available",
#     "stdout_lines": [
#       "PLAY [localhost] ***************************************************************",
#       "",
#       "TASK [test1 : TEST 1 | Basic] **************************************************",
#       "ok: [localhost] => {",
#       "    \"msg\": \"TEST 1: 'NOT SET'\"",
#       "}",
#       "",
#       "TASK [test1 : TEST 1 | Checking environmental variable] ************************",
#       "skipping: [localhost]",
#       "",
#       "TASK [test1 : TEST 1 | Showing environmental variable] *************************",
#       "skipping: [localhost]",
#       "",
#       "TASK [test1 : TEST 1 | Sleeping] ***********************************************",
#       "skipping: [localhost]",
#       "",
#       "TASK [test1 : TEST 1 | Fail] ***************************************************",
#       "skipping: [localhost]",
#       "",
#       "PLAY RECAP *********************************************************************",
#       "localhost                  : ok=1    changed=0    unreachable=0    failed=0    skipped=4    rescued=0    ignored=0"
#     ],
#     "stderr_lines": [
#       "[WARNING]: No inventory was parsed, only implicit localhost is available"
#     ]
#   }
# }

# to stop a running execution
e = Execution(c)
e.run(blocking=False)
e.stop()  # executor sends signals to subprocess running ansible
```

----

## Contribute

We are happy to see contributions. (:

* Report issues
* Create feature-requests
* Provide PR's for:
  * more Unit-Tests
  * more Integration-Tests
  * fixing bugs/errors
  * enhancing the input-validation
  * ...


----

## AI-Usage Info

The coding of this project involved minimal AI-usage.
