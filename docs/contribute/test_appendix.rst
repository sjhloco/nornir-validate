Unittest Appendix
=================

Test files
----------

- **conftest.py**: Shared, session-scoped Nornir inventory fixture (``nr``) and the ``fake_netmiko`` factory fixture used to test the engine tasks without a device
- **test_core.py**: Pure helpers in *core.py*, plus the ``validate`` and ``generate_val_file`` engine tasks
- **test_compliance_report.py**: Report semantics (pass/fail/skip, ``_mode: strict``, numeric forms) and file saving in *compliance_report.py*
- **test_validations.py**: Per-os_type command validations (desired_state, cmd_output, actual_state, report) built dynamically from the index files - see below

If a change is about a specific os_type/feature's commands or parsing, it belongs in *test_validations.py*; if it's about the Nornir orchestration (command dispatch, report/file writing) or a helper function, it belongs in *test_core.py* or *test_compliance_report.py*.

Testing the engine without a device
------------------------------------

``validate`` and ``generate_val_file`` reference ``netmiko_send_command`` as a module global, resolved at call time, so it can be intercepted with ``monkeypatch.setattr(core, "netmiko_send_command", fake_netmiko({cmd: output}))``. The ``fake_netmiko`` fixture (in *conftest.py*) builds a fake Nornir task from a ``{command: output}`` map; a mapped value that is an ``Exception`` instance is raised instead of returned, to drive the failure paths. Use ``tmp_path`` for ``directory=``/``save_report=`` so the real file-writing code runs.

Per-os_type command validations
--------------------------------

There are 5 sets of per-os_type unit tests grouped under their own class to allow for running for individual os_type feature or all os_type and features, plus 2 guard classes that aren't parametrised per os_type/feature. *test_validations.py* uses the index files to dynamically build the tests to simplify things so that the test files do NOT need updating when new sub-features are added.

**test_command_templating:** Renders *"subfeature_index.yml"* with *"xx_desired_state.j2"* and compares result against the file *"xx_commands.yml"*

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestCommands::test_command_templating[<os_type>_<feature>]' -vv
    uv run pytest 'tests/test_validations.py::TestCommands' -vv

**test_create_validation:** Formats *"xx_cmd_output.json"* with *"xx_actual_state.generate_val_file"* and compares result against the file *"xx_validate.yml"*

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestValFile::test_create_validation_file[<os_type>_<feature>]' -vv
    uv run pytest 'tests/test_validations.py::TestValFile' -vv

**test_desired_state_templating:** Renders *"xx_validate.yml"* with *"xx_desired_state.j2"* and compares result against the file *"xx_desired_state.yml"*

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestDesiredState::test_desired_state_templating[<os_type>_<feature>]' -vv
    uv run pytest 'tests/test_validations.py::TestDesiredState' -vv

**test_actual_state_formatting:** Formats *"xx_cmd_output.json"* with *"xx_actual_state.format_actual_state"* and compares result against the file *"xx_actual_state.yml"*

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestActualState::test_actual_state_formatting[<os_type>_<feature>]' -vv
    uv run pytest 'tests/test_validations.py::TestActualState' -vv

**test_report_passes:** Validates a compliance report comparing the files *"xx_desired_state.yml"* and *"xx_actual_state.yml"* passes

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestComplianceReport::test_report_passes[<os_type>_<feature>]' -vv
    uv run pytest 'tests/test_validations.py::TestComplianceReport' -vv

**test_index_and_test_file_consistency:** Guards the directory-scanning design the rest of this file's tests rely on - that every index file feature/sub-feature has matching *feature_templates* and *tests/os_test_files* fixtures, and vice versa

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestIndexIntegrity' -vv

**test_format_actual_state_unknown_subfeature / test_set_keys_unknown_os_type:** Pins the defensive raises (``ValueError``/``NotImplementedError``) common to every *feature_templates* module, parametrised dynamically over all of them

.. code-block:: bash

    uv run pytest 'tests/test_validations.py::TestDefensiveRaises' -vv

**test_all:** Run all validations, so all classes.

.. code-block:: bash

    uv run pytest tests/test_validations.py -vv
