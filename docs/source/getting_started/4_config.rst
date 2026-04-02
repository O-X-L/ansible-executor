.. _start_config:

.. include:: ../_include/head.rst

.. include:: ../_include/head_getting_started.rst

==========
4 - Config
==========

.. include:: ../_include/warn_develop.rst

Runner Config
#############


Ansible Config
##############

The runner-config only handles the most important settings that are required to get the execution started.

If you want to pass other settings to Ansible - you can:

* Set Environmental-Variables as seen `in the official Ansible documentation <https://docs.ansible.com/projects/ansible/latest/reference_appendices/config.html#common-options>`_
* Use an :code:`ansible.cfg` file placed inside your :code:`project_dir`
* Use Ansible-Variables on inventory- or playbook-level
