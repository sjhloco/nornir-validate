![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nornir-validate)
![PyPI - Version](https://img.shields.io/pypi/v/nornir-validate)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Documentation Status](https://readthedocs.org/projects/nornir-validate/badge/?version=latest)](https://nornir-validate.readthedocs.io/en/latest/?badge=latest)

# Nornir Validate

A Nornir plugin for validating network state (*actual state*) against YAML-based specifications (*desired state*). This project extends [napalm-validate](https://github.com/napalm-automation/napalm/blob/develop/napalm/base/validate.py) to perform command-based validation rather than relying solely on getters, providing greater flexibility in validating arbitrary command outputs. It leverages Nornir with `nornir-netmiko` to collect and format device data, then compares ***actual state*** against ***desired state*** to generate a ***compliance report***.

For a complete list of supported validations, see the [validation reference](https://nornir-validate.readthedocs.io/en/latest/validations.html).

## How It Works

1. **Validation File**: The expected *desired state* specified in YAML format (can be automatically generated) is provided at runtime
2. **Desired State**: The *validation file* is rendered by Jinja adding validation commands to the *desired state* and storing this as a Nornir host variable
3. **Data Collection**: *Nornir* (*netmiko* plugin) executes commands against target devices parsing the outputs through `ntc-templates` to construct the *actual state*
4. **Compliance Report**: The *desired state* and *actual state* are fed into *napalm_validate* generating a *compliance report* of the differences

![Image](https://github.com/user-attachments/assets/5f80656a-6ed5-405e-99f1-1c4cfb4281e8)

## Installation

```bash
pip install nornir-validate
```

or

```bash
uv add nornir-validate
```

## Usage

Below is just the bare minimum to get started, see the [documentation](https://nornir-validate.readthedocs.io/en/latest/index.html#) for more detailed information.

### Generating a Compliance Report

The compliance report is generated based on a YAML formatted validation file describing the desired state of the network. Comprehensive validation file examples for all supported operating systems and features can be found in the [example_validation_files](https://github.com/sjhloco/nornir-validate/tree/main/example_validation_files>) directory.

```python
import yaml
from nornir import InitNornir
from nornir_validate import validate, print_result_val

nr = InitNornir(config_file="config.yml")

with open("input_val_data.yml") as tmp_data:
    input_data = yaml.load(tmp_data, Loader=yaml.Loader)

result = nr.run(task=validate, input_data=input_data)
print_result_val(result)
```

By default the full compliance report will be printed to the screen if the validation fails, add the `save_report=""` argument to also save it to file.

### Auto-generation of Validation Files

Rather than defining validation files manually from scratch they can be automatically generated from a devices actual state based of an **index of sub-features**. If no index file is specified (omit the `input_data=` argument), validations will be generated for **all enabled sub-features** on the device.

```python
from nornir import InitNornir
from nornir_validate import generate_val_file, print_result_gvf

nr = InitNornir(config_file="config.yml")

with open("CORE_index.yml") as tmp_data:
    input_idx = yaml.load(tmp_data, Loader=yaml.Loader)

result = nr.run(task=generate_val_file, input_data=input_idx)
print_result_gvf(result, nr)
```

Validations that have *environment-specific* elements (such as VRF route table) must be manually defined in the index file, if not it will only generate validations for the global elements (the global routing table).

## Example projects

Below are few projects that use *nornir-validate*:

- [nr-val](https://github.com/sjhloco/nr-val): A basic no-frills script to generate validation files and create compliance reports
- [nornir-ppcheck](https://github.com/sjhloco/nornir-ppcheck): Tool for running pre and post change check as well as validation of network state
- [update-mgmt-acl](https://github.com/sjhloco/update-mgmt-acl): Tool to update management and SNMP ACLs on Cisco IOS-XE, NXOS and ASA

## Contributing

If you want to help add any validations to the project the [Contribution Guidelines](https://nornir-validate.readthedocs.io/en/latest/contribute/index.html) walk through the steps.
