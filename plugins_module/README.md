# Ansible-Playbook Executor - Ansible Plugins

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

This module contains Ansible-plugins for use with the [oxl-ansible-executor](https://github.com/O-X-L/ansible-executor).

Source code: [oxl-ansible-executor-plugins](https://github.com/O-X-L/ansible-executor/tree/latest/plugins_module)

### Execution Stats

If you want to have access to execution-stats - make sure to install and enable the plugin:

```
# inside the execution-venv or -container
pip install oxl-ansible-executor-plugins

# enable the plugin by adding its path to the env-variable
ANSIBLE_CALLBACK_PLUGINS="${ANSIBLE_CALLBACK_PLUGINS:+${ANSIBLE_CALLBACK_PLUGINS}:}$(oxl-ansible-executor-plugins-callback)"
```

----

## Manual testing

To test the plugins manually, you have to tell Ansible were to find them AND to enable them.

```bash
# install module if you do not want to manually create the plugin-files
pip install oxl-ansible-executor-plugins

# if installed - get the plugin-directory using the helper-script
oxl-ansible-executor-plugins-callback

# point ansible to the directory containing the plugins
export ANSIBLE_CALLBACK_PLUGINS=./callback_plugins

# enable the plugins
export ANSIBLE_CALLBACKS_ENABLED=oxl_executor_stats_recap,oxl_executor_stats_live

# run ansible
ansible-playbook ...
```

