Generating a Compliance Report
==============================

Overview
--------

The compliance report is generated based on a YAML-formatted validation file that describes the desired state of the network. The input data is organized into three primary dictionaries, each of which can define the entire feature set or a subset of features.

- **hosts:** Host name dictionaries containing sub-dicts of host-specific features to be validated
- **groups:** Group name dictionaries of group-specific features to be validated
- **all:** Dictionary of variables defining features that apply across *all* hosts

.. note::

  The hostname or group name must match exactly those defined in the Nornir inventory.  
  In cases where there are conflicts between feature definitions, *groups* take precedence 
  over *all* and *hosts* over *groups* (``hosts > groups > all``).

Validation Examples
-------------------

The following validation file example demonstrates the inheritance mechanism, it would validate:

- The port-channel state and port membership for **all** devices
- The image version for devices in the **iosxe** group
- The OSPF interfaces and neighbors on host **HME-RTR01**

.. code-block:: yaml

  all:
    intf_bonded:
      port_channel:
        Po2:
          protocol: LACP
          members: [Gi0/15, Gi0/16]
  groups:
    iosxe:
      system:
        image: 16.6.2
  hosts:
    HME-RTR01:
      route_protocol:
        ospf_intf_nbr:
          Gi1/1:
            pid: 1
            area: 0
          Vl120:
            pid: 1
            area: 0
            nbr: [192.168.10.2, 192.168.10.3]

Comprehensive examples for all supported operating systems and features can be found in the `example_validation_files <https://github.com/sjhloco/nornir-validate/tree/main/example_validation_files>`_ directory.

Running Nornir Validate
-----------------------

The validate method is imported directly into a script leveraging the existing Nornir inventory. A customised version of `nornir_rich <https://github.com/InfrastructureAsCode-ch/nornir_rich>`_ is used to print the result so that the *sub-feature* names can be incorporated into the printed results.

.. code-block:: python

    import yaml
    from nornir import InitNornir
    from nornir_validate import validate, print_result_val
  
    nr = InitNornir(config_file="config.yml")

    with open("input_val_data.yml") as tmp_data:
        input_data = yaml.load(tmp_data, Loader=yaml.Loader)

    result = nr.run(task=validate, input_data=input_data)
    print_result_val(result)

Alternatively, you can just feed the data in direct rather than loading it from a file.

.. code-block:: python

    input_data = {
        "groups": {
            "ios": {
                "intf_bonded": {
                    "port_channel": {
                        "Po1": {"protocol": "LACP", "members": ["Gi0/2", "Gi0/3"]}
                    }
                },
            }
        }
    }
    result = nr.run(task=validate, input_data=input_data)
    print_result_val(result)

By default the compliance report is printed to screen only if the validation fails (Nornir task marked as failed), add the ``print_report=True`` argument to also print the report if the validation passes. The report can also be saved to file (*hostname_compliance_report_YYYYMMDD-HHMM.json*), add ``save_report=`` with an explicit directory path or ``""`` for the current directory.

.. code-block:: python

  result = nr.run(task=validate, input_data=input_data, print_report=True, save_report="")

Compliance Report
-----------------

The compliance report compares desired and actual state via *napalm-validate* (are iterated through it), producing sub-feature-level compliance entries that aggregate into an overall compliance status. Any failure (strict mismatch, missing peer, etc.) marks the report as **non-compliant**.

.. figure:: /_static/images/failed_compliance_report.png
   :alt: Failed compliance report example
   :width: 100%
   :align: center

   Example of a failed report due to global routing table missing 1 route (all other validations comply)

Skipped validations
~~~~~~~~~~~~~~~~~~~

Not every feature is supported on every OS type, so a validation can be requested for a device that has no command to gather it. Rather than being dropped silently these are listed under a ``skipped`` key of *feature.sub_feature* names and the Nornir task is marked as failed.

.. code-block:: python

    {'system.image': {...}, 'skipped': ['layer2.vlan']}

A skipped validation is not the same as a non-compliant one, the overall ``complies`` value still reflects only what actually ran. If this happens it normally means a feature is listed under the ``all`` dictionary but is only valid for some of the OS types being validated, move it to the relevant ``groups`` or ``hosts`` dictionary instead.

.. figure:: /_static/images/compliant_with_skipped.png
   :alt: Compliant report with skipped
   :width: 100%
   :align: center

   Example of a compliant report but with skipped sub-features

A sub-feature with an *empty* desired state (``{}``) is not skipped, it holds nothing to assert against so there is nothing that could be run. ``generate_val_file`` writes these for a sub-feature that isn't in use on the device, so a generated validation file still complies when fed straight back in. These are ignored entirely rather than skipped, so are absent from the compliance report and the ``skipped`` list. If a sub-feature you expected is missing from the report, check whether it has an empty desired state in the validation file.

.. code-block:: yaml

    intf_bonded:
      port_channel: {}      # ignored, absent from the report

This applies to validation only. ``generate_val_file`` deliberately tries every feature against a device to discover what is enabled, so therefore any feature without a command for that OS type is ignored rather than skipped.