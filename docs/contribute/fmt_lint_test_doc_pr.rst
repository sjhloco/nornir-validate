Format, test, document and PR
=============================

Below are the steps to fork and contribute to this project.

1. Fork and Clone
-----------------

Create a fork of `nornir-validate <https://github.com/sjhloco/nornir-validate/tree/main/src/nornir_validate>`_, download (*git clone*) a local copy of it and add the original repo as a remote.

.. code-block:: bash

    git clone git@github.com:<your_github_username>/nornir-validate.git
    cd nornir-validate
    git remote add upstream https://github.com/sjhloco/nornir-validate.git

2. Python venv and pre-test
---------------------------

Create the Python virtual environment and run all the workflow actions to prove everything is as it should be before starting out.

- `Ruff Formatter <https://docs.astral.sh/ruff/formatter/>`_ is a code formatter for Python that focuses on speed and correctness, similar to black but with a different design philosophy
- `Ruff Linter <https://docs.astral.sh/ruff/linter/>`_ is an extremely fast Python linter designed as a drop-in replacement for Flake8, isort, pydocstyle, pyupgrade, autoflake, and more
- `MyPy <https://mypy-lang.org>`_ performs static type checking
- `PyTest <https://docs.pytest.org/en/stable/>`_ unit-tests validates core nornir-validate functions and all of the feature templates

.. code-block:: bash

    uv sync
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy .
    uv run pytest -v

.. note::

    This documentation assumes you are using `uv <https://docs.astral.sh/uv/>`_ for python and package management, if you are using pip use ``pip install -r requirements.txt`` and remove ``uv run`` from the commands. 

To check test coverage (a one-off diagnostic, not a project dependency) use the ``--with`` flag to run *pytest-cov* from an ephemeral overlay.

.. code-block:: bash

    uv run --with pytest-cov pytest --cov=src/nornir_validate --cov-report=term-missing

3. Branch and make changes
--------------------------

Create a new branch for your work, if you are adding a new validation see the proceeding pages for steps on using the ``feature_builder.py`` script to do so.

.. code-block:: bash

    git checkout -b add_paloalto_panos_show_routing_resource

4. Format, lint, typing and test
--------------------------------

The project settings for all of these tools can be found in *pyproject.toml*, they are used when running the tools locally and when the Github workflow actions are run as part of the PR.

.. code-block:: bash

    uv run ruff format --check .
    uv run ruff check .
    uv run mypy .

Before doing the unit testing use the *rebuild_test_files.py* script to re-build the test files (*-ds, -as, -vf*), unless a breaking change has been made to a sub-feature you shouldn't really be seeing any changes to these existing files.

.. code-block:: bash

    uv run scripts/rebuild_test_files.py
    uv run pytest -vv

5. Documentation
----------------

For new validations the `Read The Docs (RTD) validation table <https://github.com/sjhloco/nornir-validate/blob/main/docs/validations.rst>`_ needs updating, if you feel the validation requires more details (unusual to need it) also add an entry in the **Validation-specific details** section.

To test documentation changes install the **docs** *dependency-group* packages (*sphinx, sphinx-rtd-theme*), build the site locally (in *_build*) and use the `Live Server <https://github.com/ritwickdey/vscode-live-server/tree/2669d78c8ff22e4d5b3f664523c3400c5893ec6f>`_ VScode extension to launch the site and check that the table is formatted correctly in a browser. 

.. code-block:: bash

    uv sync --group docs
    cd docs
    uv run make html 
    
Once finished cleanup the html build as it is no longer needed, the external RTD site will be automatically rebuilt once the PR has been approved and your branch successfully merged.

.. code-block:: bash

    uv run make clean
    
6. Example validations
----------------------

Working examples of features/sub-features need adding to the `example_validation_files <https://github.com/sjhloco/nornir-validate/tree/main/example_validation_files>`_, do so in the os_specific *xx_validations.yml* and *all_validations.yml* (only needed if is a new sub-feature) files.

7. Commit, push and PR
----------------------

Stage, commit and push your changes (branch) back to your remote branch.

.. code-block:: bash

    git add .
    git commit -m 'feat(paloalto_panos): Add new template for paloalto_panos show routing resource'
    git push origin add_paloalto_panos_show_routing_resource

Before submitting the PR the below MUST always be true:

- All Ruff, MyPy and unit tests PASS
- RTD documentation UPDATED
- New validations ADDED to the examples
