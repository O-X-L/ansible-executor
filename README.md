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

**DISCLAIMER**: This is an **unofficial community project**! Do not confuse it with the vanilla [Ansible/Ansible-Runner](https://ansible.com/) product!

**WARNING**: This project is still in early development. DO NOT use it in production!

----

## Scope

The scope of this project is it to create a simple and transparent Python3-interface that can be used to execute Ansible-playbooks.

It will focus on using docker or podman to execute ansible in an isolated environment. But local execution will also be available.

The implementation will be opinionated and will have a 'narrow' interface.

### Motivation

I was not 100% happy with the official [ansible-runner](https://github.com/ansible/ansible-runner) library.

It provides a lot more functionality than we actually need (*only executing ansible-playbooks*) and thus has a lot more complexity added-on. This makes it also hard to troubleshoot.

As I needed an alternative I wanted to provide it to the community to play with. (:

I will try to create a transparent documentation and a lot of unit- & integration-tests!

Feel free to give feedback as [GitHub issues](https://github.com/O-X-L/ansible-executor/issues) or [email](mailto://contact+ansibleexecutor@oxl.at).

----

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
    - [x] Playbook targeting remote Linux server (SSH-Key, Connect-Pass, Become-Pass, Vault-Pass)
      - [x] Pass secrets via one-time-read Pipes/FIFO (*in-memory - does not write to disk*)
    - [x] Stopping job
    - [x] Redirect output (stdout/stderr) to log-files
    - [ ] Playbook Status (*per category, per host*)
      - [ ] Track stati at runtime
- [ ] Tests
  - [ ] Unit-Tests for all components (>85% coverage)
    - [x] Execution Config-Validation
    - [ ] Execution
      - [ ] Before
        - [ ] Base-Executor
        - [ ] Local Executor-Engine
        - [ ] Containerized Executor-Engine
      - [ ] After
      - [ ] Execution-Status
  - [ ] Integration-Tests for many practical use-cases
    - [x] Simple execution targeting localhost
    - [x] Passing extra-vars
    - [x] Passing env-vars
    - [x] Enabling output-colors
    - [x] User stopping execution
    - [x] Execution reached timeout
    - [x] Passing secrets (as value & as file)
      - [x] SSH-Key (*via ssh-agent*)
      - [x] Connect-Pass
      - [x] Become-Pass
      - [x] Ansible-Vault
    - [ ] SSH
      - [x] SSH-Key usage
      - [ ] Known-Hosts file
    - [ ] tbc...
  - [ ] Integration-Tests also for containerized executor

----

## Install

```
pip install oxl-ansible-executor
```

See: [pypi.org/oxl-ansible-executor](https://pypi.org/project/oxl-ansible-executor/)

----

## Usage

```python3
from oxl_ansible_executor import Execution, ExecutionConfig

c = ExecutionConfig(
  playbook_dir='/home/demo/ansible/',
  playbook_file='test.yml',
  inventory_files='inv/env1/hosts.yml',
)
e = Execution(c)

e.run(blocking=True)
# [INFO] Creating log-files
# [INFO] Using executor: local
# [INFO] Creating secret-pipes
# [INFO] Using log files: /home/demo/.local/share/oxl-ansible-executor/ansible_stdout_1775500760_lhWOT.log & /home/demo/.local/share/oxl-ansible-executor/ansible_stderr_1775500760_lhWOT.log
# [INFO] Executing ansible-playbook
# [INFO] Command: ['ssh-agent', 'sh', '-c', 'ssh-add /tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw && /home/demo/.venv/bin/ansible-playbook -i inv/abc/hosts.yml -C -D -l srv1 --key-file /tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw --become-pass-file /tmp/ar_znjp4bih/.SHVTpOYOH93aaZBTAgVJ --vault-pass-file /tmp/ar_znjp4bih/.GwkiXZ7YrpEvGY8BnyF2 syslog.yml']

print(e.status)
# {
#   "finished": true,
#   "playbook_finished": true,
#   "failed": false,
#   "canceled": false,
#   "time_start": 1775500758,
#   "time_finish": 1775500783,
#   "timed_out": false,
#   "time_duration_sec": 25,
#   "log_stdout_file": "/home/demo/.local/share/oxl-ansible-executor/ansible_stdout_1775500760_lhWOT.log",
#   "log_stderr_file": "/home/demo/.local/share/oxl-ansible-executor/ansible_stderr_1775500760_lhWOT.log",
#   "ansible_command": [
#     "ansible-playbook",
#     "-i",
#     "inv/abc/hosts.yml",
#     "-C",
#     "-D",
#     "-l",
#     "srv1",
#     "--key-file",
#     "/tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw",
#     "--become-pass-file",
#     "/tmp/ar_znjp4bih/.SHVTpOYOH93aaZBTAgVJ",
#     "--vault-pass-file",
#     "/tmp/ar_znjp4bih/.GwkiXZ7YrpEvGY8BnyF2",
#     "syslog.yml"
#   ],
#   "process_command": [
#     "ssh-agent",
#     "sh",
#     "-c",
#     "ssh-add /tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw && /home/demo/.venv/bin/ansible-playbook -i inv/abc/hosts.yml -C -D -l srv1 --key-file /tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw --become-pass-file /tmp/ar_znjp4bih/.SHVTpOYOH93aaZBTAgVJ --vault-pass-file /tmp/ar_znjp4bih/.GwkiXZ7YrpEvGY8BnyF2 syslog.yml"
#   ],
#   "process_rc": 0,
#   "process_result": {
#     "failed": false,
#     "rc": 0,
#     "pid": null,
#     "stdout": "<OMITTED FOR DEMO>",
#     "stderr": "<OMITTED FOR DEMO>",
#     "stdout_lines": [
#       "PLAY [all] *********************************************************************",
#       "",
#       "TASK [Install rsyslog & logrotate] *********************************************",
#       "ok: [srv1]",
#       "",
#       "TASK [Add certificates] ********************************************************",
#       "ok: [srv1] => (item={'c': '-----BEGIN CERTIFICATE-----\\nMIIDdjCCAv2gAwIBAgIUUkucdMI33le6pBxGgw6WRP2yPlcwCgYIKoZIzj0EAwIw\\ngZExCzAJBgNVBAYTAkFUMQ8wDQYDVQQIDAZTdHlyaWExDTALBgNVBAcMBEdyYXox\\nGDAWBgNVBAoMD09YTCBJVCBTZXJ2aWNlczESMBAGA1UECwwJTG9nc2VydmVyMRUw\\nEwYDVQQDDAxMb2dzZXJ2ZXIgQ0ExHTAbBgkqhkiG9w0BCQEWDmNvbnRhY3RAb3hs\\nLmF0MB4XDTI0MTIyNDEzMjExOFoXDTQ0MTIxOTEzMjExOFowgZExCzAJBgNVBAYT\\nAkFUMQ8wDQYDVQQIDAZTdHlyaWExDTALBgNVBAcMBEdyYXoxGDAWBgNVBAoMD09Y\\nTCBJVCBTZXJ2aWNlczESMBAGA1UECwwJTG9nc2VydmVyMRUwEwYDVQQDDAxMb2dz\\nZXJ2ZXIgQ0ExHTAbBgkqhkiG9w0BCQEWDmNvbnRhY3RAb3hsLmF0MHYwEAYHKoZI\\nzj0CAQYFK4EEACIDYgAEUwaiRMy1OcN0j5odvoTir6LFAqAlUlDp708Y39ZdFduv\\nXMEJGKWeHUKnoMT4uaDEomlwqEUa5JcG3Z9R0PeCJsNXvns53uK1j1uMY395yIvW\\nyQ8yu1vDhD/OnnOMl6oro4IBEjCCAQ4wDAYDVR0TBAUwAwEB/zAdBgNVHQ4EFgQU\\nvk1BL8cxa/eNRSQDD/T+yTyA7sswgdEGA1UdIwSByTCBxoAUvk1BL8cxa/eNRSQD\\nD/T+yTyA7suhgZekgZQwgZExCzAJBgNVBAYTAkFUMQ8wDQYDVQQIDAZTdHlyaWEx\\nDTALBgNVBAcMBEdyYXoxGDAWBgNVBAoMD09YTCBJVCBTZXJ2aWNlczESMBAGA1UE\\nCwwJTG9nc2VydmVyMRUwEwYDVQQDDAxMb2dzZXJ2ZXIgQ0ExHTAbBgkqhkiG9w0B\\nCQEWDmNvbnRhY3RAb3hsLmF0ghRSS5x0wjfeV7qkHEaDDpZE/bI+VzALBgNVHQ8E\\nBAMCAQYwCgYIKoZIzj0EAwIDZwAwZAIwHbFj7SEsIg3dUBpAkKIfLWVrpKicxDUe\\nKqUd/hcXHX/TTKKd0yehyXhZR0HBYgHEAjAbxJb8pQIVzCowHcXmv790wOiSsaFL\\nQJuH8qil1t0JSAV73EdK9zM+IDdvBVdDlBw=\\n-----END CERTIFICATE-----\\n', 'f': 'log_ca.crt'})",
#       "ok: [srv1] => (item={'c': '-----BEGIN CERTIFICATE-----\\nMIIDgTCCAwagAwIBAgIQX7p1IkBq4b97O8k0caiMfjAKBggqhkjOPQQDAjCBkTEL\\nMAkGA1UEBhMCQVQxDzANBgNVBAgMBlN0eXJpYTENMAsGA1UEBwwER3JhejEYMBYG\\nA1UECgwPT1hMIElUIFNlcnZpY2VzMRIwEAYDVQQLDAlMb2dzZXJ2ZXIxFTATBgNV\\nBAMMDExvZ3NlcnZlciBDQTEdMBsGCSqGSIb3DQEJARYOY29udGFjdEBveGwuYXQw\\nHhcNMjQxMjI0MTQyNzA4WhcNMjkxMjIzMTQyNzA4WjCBjDELMAkGA1UEBhMCQVQx\\nDzANBgNVBAgMBlN0eXJpYTENMAsGA1UEBwwER3JhejEYMBYGA1UECgwPT1hMIElU\\nIFNlcnZpY2VzMRIwEAYDVQQLDAlMb2dzZXJ2ZXIxEDAOBgNVBAMMB2dlbmVyaWMx\\nHTAbBgkqhkiG9w0BCQEWDmNvbnRhY3RAb3hsLmF0MHYwEAYHKoZIzj0CAQYFK4EE\\nACIDYgAEF2uLX4WUd/4byt3aS59XxohILfEdnNvqdg87nG0PXC85yhtB5yKMWryT\\n+cWZeGYSucdLtZ4UxDqvosQ32eql/K+VoVRqkb4UF1Mmgq5+smhHIkVxFjJCUtsg\\ni+G9aPM/o4IBJDCCASAwCQYDVR0TBAIwADAdBgNVHQ4EFgQUmULR2FK41wLFEl/B\\nSGhYkQ0Z5v8wgdEGA1UdIwSByTCBxoAUvk1BL8cxa/eNRSQDD/T+yTyA7suhgZek\\ngZQwgZExCzAJBgNVBAYTAkFUMQ8wDQYDVQQIDAZTdHlyaWExDTALBgNVBAcMBEdy\\nYXoxGDAWBgNVBAoMD09YTCBJVCBTZXJ2aWNlczESMBAGA1UECwwJTG9nc2VydmVy\\nMRUwEwYDVQQDDAxMb2dzZXJ2ZXIgQ0ExHTAbBgkqhkiG9w0BCQEWDmNvbnRhY3RA\\nb3hsLmF0ghRSS5x0wjfeV7qkHEaDDpZE/bI+VzALBgNVHQ8EBAMCBaAwEwYDVR0l\\nBAwwCgYIKwYBBQUHAwIwCgYIKoZIzj0EAwIDaQAwZgIxAKVAFBs4EaCRx/0VEZKA\\n3/n06CaEE5I05v8kN5XBWgbJPxaDi+bcRJrzBMsn/JRjvwIxAMi4cekyGCWZYDtM\\n+8WRliIMba5dbFuR/UGAf/bIfmNWM2sSqtzseSZ/RoPdjaChlQ==\\n-----END CERTIFICATE-----\\n', 'f': 'log_client.crt'})",
#       "",
#       "TASK [Add certificate key] *****************************************************",
#       "ok: [srv1]",
#       "",
#       "TASK [Add graylog forwarding] **************************************************",
#       "ok: [srv1]",
#       "",
#       "TASK [Software log files] ******************************************************",
#       "ok: [srv1]",
#       "",
#       "TASK [Software log rotation] ***************************************************",
#       "ok: [srv1]",
#       "",
#       "TASK [Restart services] ********************************************************",
#       "changed: [srv1] => (item=rsyslog.service)",
#       "changed: [srv1] => (item=logrotate.service)",
#       "",
#       "PLAY RECAP *********************************************************************",
#       "srv1                       : ok=7    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0"
#     ],
#     "stderr_lines": [
#       "Identity added: /tmp/ar_znjp4bih/.fIWqOdKaPzGioFfDljSw (Demo)"
#     ]
#   }
# }

# to stop a running execution
e = Execution(c)
e.run(blocking=False)
# you could 'tail -f' the log files
e.stop()  # executor sends signals to subprocess running ansible
```

----

## Use-Cases

See: Our simple [Ansible WebUI](https://github.com/O-X-L/ansible-webui)

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

## Security Considerations

* Secrets are passed to Ansible via [one-time-readable FIFO/Pipes](https://github.com/O-X-L/ansible-executor/blob/latest/src/oxl_ansible_executor/runner_execution.py#L164)
* SSH-agent is used to pass SSH-keys to Ansible
* Files are created with an explicit `0600` file-mode
* By default, the temporary runtime-directory is removed after the execution has finished (*only log-files remain - see example above*)
* tbc

----

## AI-Usage Info

The coding of this project involved minimal AI-usage.
