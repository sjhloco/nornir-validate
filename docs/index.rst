Nornir Validate Documentation
=============================

A Nornir plugin for validating network state (*actual state*) against YAML-based specifications (*desired state*). This project extends `napalm-validate <https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py>`_ to perform command-based validation rather than relying solely on getters, providing greater flexibility in validating arbitrary command outputs. It leverages Nornir with `nornir-netmiko` to collect and format device data, then compares **actual state** against **desired state** to generate a **compliance report**.

How It Works
------------

1. **Validation File**: The expected *desired state* specified in YAML format (can be automatically generated) is provided at runtime
2. **Desired State**: The *validation file* is rendered by `Jinja <https://jinja.palletsprojects.com/en/stable/>`_ adding validation commands to the *desired state* and storing this as a Nornir host variable
3. **Data Collection**: `Nornir <https://github.com/nornir-automation/nornir>`_ (`netmiko plugin <https://github.com/ktbyers/nornir_netmiko>`_) executes commands against target devices parsing the outputs through `ntc-templates <https://github.com/networktocode/ntc-templates>`_ to construct the *actual state*
4. **Compliance Report**: The *desired state* and *actual state* are fed into `napalm-validate <https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py>`_  generating a *compliance report* of the differences

.. figure:: /_static/images/terminalizer_val_example.gif
   :alt: Compliance report animation
   :width: 100%
   :align: center

   Example of a non-compliant and compliant report

Contents
--------

* :doc:`Validations <validations>` - A table of all the current supported validations and validation nuances
* :doc:`Tutorial <tutorial/index>` - Contains all the information you require to get started with nornir-validate
* :doc:`Contribute <contribute/index>` - Runs through how to contribute new validation models to the project

.. toctree::
   :hidden:
   :maxdepth: 3

   Home <self>
   validations
   tutorial/index
   contribute/index
