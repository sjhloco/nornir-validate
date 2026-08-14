"""Shared fixtures for test_core.py and test_compliance_report.py."""

import os
from collections.abc import Callable
from typing import Any

import pytest
from nornir import InitNornir
from nornir.core import Nornir
from nornir.core.task import Result, Task

TEST_INVENTORY = os.path.join(os.path.dirname(__file__), "test_inventory")


@pytest.fixture(scope="session")
def nr() -> Nornir:
    """Nornir inventory (one host per os_type) shared across the engine/report tests."""
    return InitNornir(
        inventory={
            "plugin": "SimpleInventory",
            "options": {
                "host_file": os.path.join(TEST_INVENTORY, "hosts_validations.yml"),
                "group_file": os.path.join(TEST_INVENTORY, "groups.yml"),
            },
        },
        logging={"enabled": False},
    )


@pytest.fixture
def fake_netmiko() -> Callable[[dict[str, Any]], Callable[..., Result]]:
    """Factory that builds a fake netmiko_send_command Nornir task from a {command: output} map.

    Used with `monkeypatch.setattr(core, "netmiko_send_command", fake_netmiko({...}))` to test
    `validate`/`generate_val_file` without a real device connection. A mapped value that is an
    Exception instance is raised instead of returned, to drive the failure paths.
    """

    def make_fake(command_map: dict[str, Any]) -> Callable[..., Result]:
        def fake(
            task: Task,
            command_string: str,
            use_textfsm: bool = True,  # noqa: ARG001
            **kwargs: object,  # noqa: ARG001
        ) -> Result:
            output = command_map[command_string]
            if isinstance(output, Exception):
                raise output
            return Result(host=task.host, result=output)

        return fake

    return make_fake
