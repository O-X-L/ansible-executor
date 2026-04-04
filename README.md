# Ansible Runner minimal

<p align="center">
    <a title="Support this Project (Donate, Support-Licenses)" href="https://shop.oxl.app/collections/open-source">
        <img src="https://files.oxl.at/img/badge-oss-support.svg" alt="Support Badge (Donate, Support-Licenses)"/>
    </a>
</p>

----

[![Check Docs](https://github.com/O-X-L/ansible-runner/actions/workflows/check_docs.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-runner/actions/workflows/check_docs.yml)
[![Lint](https://github.com/O-X-L/ansible-runner/actions/workflows/lint.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-runner/actions/workflows/lint.yml)
[![Unit-Tests](https://github.com/O-X-L/ansible-runner/actions/workflows/unit_test.yml/badge.svg?branch=latest)](https://github.com/O-X-L/ansible-runner/actions/workflows/unit_test.yml)

**DISCLAIMER**: This is an **unofficial community project**! Do not confuse it with the vanilla [Ansible](https://ansible.com/) product!

**WARNING**: This project is still in early development. DO NOT use it in production!

## Scope

The scope of this project is it to create a minimalistic Ansible-Runner Python3-interface that can be used to execute Ansible-playbooks.

It will focus on using docker or podman to execute ansible in an isolated environment. But local execution will also be available.

The implementation will be opinionated and will have a 'narrow' interface.

## Use-Cases

See: Our simple [Ansible WebUI](https://github.com/O-X-L/ansible-webui)

----

## Usage

```python3
from oxl_ansible_runner import Execution, ExecutionConfig

c = ExecutionConfig(
  playbook_dir='/home/abc/ansible/',
  playbook_file='test.yml',
  inventory_files='inv/env1/hosts.yml',
)
e = Execution(c)

e.run()

```

----

## Contribute

We are happy to see contributions. (:

* Report issues
* Create feature-requests
* Provide PR's for:
  * more Unit-Tests
  * fixing errors
  * enhancing the input-validation
  * ...


----

## AI-Usage Info

The coding of this project involved minimal AI-usage.
