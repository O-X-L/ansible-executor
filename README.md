# Ansible Runner minimal

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
from oxl_ansible_runner_minimal import Config, Runner

c = Config(playbook_file='test.yml', project_dir='/home/abc/ansible/', inventory_files='inv/env1/hosts.yml'
r = Runner(c)

r.run()

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
