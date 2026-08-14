"""These unittests test the operation of core.py: pure helpers, and the two Nornir engine tasks.

Use test_validations.py to test the different os_type command validations (desired_state, cmd_output, actual_state).
Use test_compliance_report.py to test compliance_report.py.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from nornir.core import Nornir
from nornir.core.exceptions import NornirSubTaskError
from nornir.core.task import AggregatedResult, MultiResult, Result, Task

from nornir_validate import core


# ----------------------------------------------------------------------------
# Nornir remembers hosts that failed a task within the session (nr fixture is session-scoped),
# reset before each test so an earlier failure/mismatch test doesn't cause a later test to
# silently skip the host.
# ----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_failed_hosts(nr: Nornir) -> None:
    nr.data.reset_failed_hosts()


# ----------------------------------------------------------------------------
# 1. HELPERS: Tests the pure helper functions
# ----------------------------------------------------------------------------
class TestHelpers:
    def test_merge_os_types(self, nr: Nornir) -> None:
        err_msg = "❌ merge_os_types: Function testing failed"
        desired_output = ["cisco_ios", "cisco_iosxe", "ios"]
        actual_output = core.merge_os_types(nr.inventory.hosts["ios_host"])
        assert actual_output == desired_output, err_msg

    def test_return_feature_desired_data(self) -> None:
        err_msg = "❌ return_feature_desired_data: Function testing failed"
        desired_output = core.return_feature_desired_data(
            {"system": {"image": "15.2(7)E2"}}
        )
        actual_output = {
            "system": {
                "file": "system_desired_state.j2",
                "sub_features": {"image": "15.2(7)E2"},
            }
        }
        assert actual_output == desired_output, err_msg

    def test_return_yaml_desired_state(self) -> None:
        err_msg = "❌ return_yaml_desired_state: Function testing failed"
        input_data = "\n- neighbor:\n    cdp:\n      show cdp neighbors:\n        Gig 0/8:\n          HME-AIR-WLC01: Gig 0/0/1\n        Gig 0/11:\n          HME-2802-AP01: Gig 0\n"
        desired_output = core.return_yaml_desired_state(input_data)
        actual_output = {
            "neighbor": {
                "cdp": {
                    "show cdp neighbors": {
                        "Gig 0/8": {"HME-AIR-WLC01": "Gig 0/0/1"},
                        "Gig 0/11": {"HME-2802-AP01": "Gig 0"},
                    }
                }
            }
        }
        assert actual_output == desired_output, err_msg

    def test_return_yaml_desired_state_numeric_gt(self) -> None:
        """The '>NN' pattern needs a workaround (yaml.Loader errors on it), pin that it still parses."""
        err_msg = "❌ return_yaml_desired_state: '>NN' numeric pattern handling failed"
        input_data = "\n- route_table:\n    route_count:\n      show ip route vrf BLU | count : >100\n"
        desired_output = core.return_yaml_desired_state(input_data)
        actual_output = {
            "route_table": {"route_count": {"show ip route vrf BLU | count": ">100"}}
        }
        assert actual_output == desired_output, err_msg

    def test_strip_empty_feat(self) -> None:
        err_msg = "❌ strip_empty_feat: Function testing failed"
        input_data = {
            "system": {"image": {"show version": "15.2(7)E2"}},
            "neighbor": {},
            "interface": {"intf": {}},
            "layer2": {"vlan": {"show vlan brief": None}},
        }
        desired_output = core.strip_empty_feat(input_data)
        actual_output = {"system": {"image": {"show version": "15.2(7)E2"}}}
        assert actual_output == desired_output, err_msg

    def test_remove_cmds_desired_state(self) -> None:
        err_msg = "❌ remove_cmds_desired_state: Function testing failed"
        input_data = {
            "intf": {
                "ip_brief": {
                    "show ip interface brief": {
                        "Loopback1": {"ip": "10.10.255.1", "status": "up"}
                    }
                }
            },
            "route_protocol": {
                "ospf_intf_nbr": {
                    "show ip ospf interface brief": "SUB_FEATURE_COMBINED_CMD",
                    "show ip ospf neighbor": {
                        "Gi0/3": {
                            "pid": 3,
                            "area": 1,
                            "nbr": {"_mode": "strict", "192.168.230.2": "FULL"},
                        }
                    },
                },
            },
        }
        desired_output = core.remove_cmds_desired_state(input_data)
        actual_output = {
            "intf": {"ip_brief": {"Loopback1": {"ip": "10.10.255.1", "status": "up"}}},
            "route_protocol": {
                "ospf_intf_nbr": {
                    "Gi0/3": {
                        "pid": 3,
                        "area": 1,
                        "nbr": {"_mode": "strict", "192.168.230.2": "FULL"},
                    }
                }
            },
        }
        assert actual_output == desired_output, err_msg

    def test_create_val_dm(self) -> None:
        """create_val_dm strips example data (dicts) from all_index.yml, leaving just sub-feature names."""
        err_msg = "❌ create_val_dm: Function testing failed"
        validations = core.create_val_dm()
        actual_output = validations["all"]["system"]
        desired_output = ["image", "mgmt_acl", "module", "sla"]
        assert actual_output == desired_output, err_msg

    def test_import_actual_state_modules_cache(self) -> None:
        """Repeat imports of the same feature are served from the module-level cache."""
        err_msg = "❌ import_actual_state_modules: Didn't return the same cached module object"
        first = core.import_actual_state_modules("system")["system"]
        second = core.import_actual_state_modules("system")["system"]
        assert first is second, err_msg

    def test_import_actual_state_modules_import_failure(self) -> None:
        """An unknown feature fails to import but doesn't raise, and isn't cached."""
        err_msg = "❌ import_actual_state_modules: Unknown feature shouldn't be cached"
        modules = core.import_actual_state_modules("nonexistent_feature_xyz")
        assert "nonexistent_feature_xyz" not in modules, err_msg

    def test_actual_state_engine_empty_output(self) -> None:
        """Empty command output produces an empty dict rather than crashing (device feature not enabled)."""
        err_msg = "❌ actual_state_engine: Empty output should produce an empty dict"
        actual_output = core.actual_state_engine(
            False, ["ios"], {"system": {"image": []}}
        )
        desired_output: dict[str, Any] = {"system": {"image": {}}}
        assert actual_output == desired_output, err_msg


# ----------------------------------------------------------------------------
# 2. TASK_DESIRED_STATE: Tests the hosts/groups/all scoping and merge precedence
# ----------------------------------------------------------------------------
def task_get_desired_state(task: Task, validations: dict[str, Any]) -> Result:
    """Runs task_desired_state and returns the resulting host_var so it can be asserted on."""
    task.run(
        task=core.task_desired_state,
        validations=validations,
        task_template=core.task_template,
    )
    return Result(host=task.host, result=task.host.get("desired_state"))


class TestTaskDesiredState:
    def test_hosts_scope(self, nr: Nornir) -> None:
        err_msg = "❌ task_desired_state: 'hosts:' scope not applied"
        validations = {"hosts": {"ios_host": {"system": {"image": "15.2(7)E2"}}}}
        result = nr.filter(name="ios_host").run(
            task=task_get_desired_state, validations=validations
        )
        actual_output = result["ios_host"][0].result
        desired_output = {"system": {"image": {"show version": "15.2(7)E2"}}}
        assert actual_output == desired_output, err_msg

    def test_groups_scope(self, nr: Nornir) -> None:
        err_msg = "❌ task_desired_state: 'groups:' scope not applied"
        validations = {"groups": {"ios": {"system": {"image": "15.2(7)E2"}}}}
        result = nr.filter(name="ios_host").run(
            task=task_get_desired_state, validations=validations
        )
        actual_output = result["ios_host"][0].result
        desired_output = {"system": {"image": {"show version": "15.2(7)E2"}}}
        assert actual_output == desired_output, err_msg

    def test_scope_merge_precedence(self, nr: Nornir) -> None:
        """Merge precedence between the three scopes.

        hosts/groups/all are rendered and merged in that order; a feature in a later scope
        overwrites the same feature from an earlier scope (current, undocumented behaviour).
        """
        err_msg = "❌ task_desired_state: 'all:' scope should take precedence over 'hosts:' for the same feature"
        validations = {
            "hosts": {"ios_host": {"system": {"image": "15.2(7)E1"}}},
            "all": {"system": {"image": "15.2(7)E2"}},
        }
        result = nr.filter(name="ios_host").run(
            task=task_get_desired_state, validations=validations
        )
        actual_output = result["ios_host"][0].result
        # 'all' rendered last, so its version of 'system' (whole feature) wins over 'hosts'
        assert actual_output["system"]["image"]["show version"] == "15.2(7)E2", err_msg

    def test_no_validations_fails(self, nr: Nornir) -> None:
        """No matching validations produces a failed Result rather than an empty host_var."""
        err_msg = "❌ task_desired_state: Empty validations should fail with a warning"
        result = nr.filter(name="ios_host").run(
            task=core.task_desired_state,
            validations={},
            task_template=core.task_template,
        )
        r = result["ios_host"][0]
        assert r.failed, err_msg
        assert "No validations were performed" in r.result, err_msg


# ----------------------------------------------------------------------------
# 3. ENGINE: Tests 'validate' and 'generate_val_file' using a fake netmiko_send_command
# ----------------------------------------------------------------------------
# Canned command output for two sub-features (ios system.image, ios layer2.vlan), scoped
# deliberately small - per-feature parsing is already covered by test_validations.py, these
# tests are about orchestration (command dispatch, output collection, report/file writing).
SHOW_VERSION_OUTPUT = [{"version": "15.2(7)E2"}]
SHOW_VLAN_BRIEF_OUTPUT = [{"vlan_id": "10", "vlan_name": "test", "interfaces": []}]
INPUT_DATA = {
    "all": {
        "system": {"image": "15.2(7)E2"},
        "layer2": {"vlan": {10: {"name": "test", "intf": []}}},
    }
}


@pytest.fixture
def ios_nr(nr: Nornir) -> Nornir:
    return nr.filter(name="ios_host")


class TestValidate:
    def test_happy_path(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko(
                {
                    "show version": SHOW_VERSION_OUTPUT,
                    "show vlan brief": SHOW_VLAN_BRIEF_OUTPUT,
                }
            ),
        )
        result = ios_nr.run(task=core.validate, input_data=INPUT_DATA)
        r = result["ios_host"][0]
        err_msg = "❌ validate: Happy path should comply and suppress the report"
        assert not r.failed, err_msg
        assert "True" in getattr(r, "report_complies", ""), err_msg
        assert r.result == "", err_msg

    def test_happy_path_print_report(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko(
                {
                    "show version": SHOW_VERSION_OUTPUT,
                    "show vlan brief": SHOW_VLAN_BRIEF_OUTPUT,
                }
            ),
        )
        result = ios_nr.run(
            task=core.validate, input_data=INPUT_DATA, print_report=True
        )
        r = result["ios_host"][0]
        err_msg = "❌ validate: print_report=True should return the full report even when it complies"
        assert r.result != "", err_msg
        assert "complies" not in r.result, err_msg

    def test_mismatch(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": SHOW_VERSION_OUTPUT}),
        )
        result = ios_nr.run(
            task=core.validate, input_data={"all": {"system": {"image": "99.9(9)E9"}}}
        )
        r = result["ios_host"][0]
        err_msg = "❌ validate: A mismatch should fail and report the diff"
        assert r.failed, err_msg
        assert "False" in getattr(r, "report_complies", ""), err_msg
        assert r.result["system.image"]["complies"] is False, err_msg
        assert (
            r.result["system.image"]["present"]["image"]["actual_value"] == "15.2(7)E2"
        ), err_msg

    def test_save_report(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": SHOW_VERSION_OUTPUT}),
        )
        result = ios_nr.run(
            task=core.validate,
            input_data={"all": {"system": {"image": "15.2(7)E2"}}},
            save_report=str(tmp_path),
        )
        r = result["ios_host"][0]
        report_files = list(tmp_path.glob("*.json"))
        err_msg = "❌ validate: save_report should write exactly one JSON report"
        assert len(report_files) == 1, err_msg
        content = json.loads(report_files[0].read_text())
        assert content["complies"] is True, err_msg
        assert content["system.image"]["complies"] is True, err_msg
        assert str(report_files[0]) in getattr(r, "report_file", ""), err_msg

    def test_command_raises_aborts_host(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
    ) -> None:
        """Unlike generate_val_file, validate does not catch NornirSubTaskError - it aborts the host."""
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": NornirSubTaskError(task=None, result=None)}),
        )
        result = ios_nr.run(
            task=core.validate, input_data={"all": {"system": {"image": "15.2(7)E2"}}}
        )
        r = result["ios_host"][0]
        err_msg = "❌ validate: A raising command should fail the whole host, not be swallowed"
        assert r.failed, err_msg
        assert isinstance(r.exception, NornirSubTaskError), err_msg


class TestGenerateValFile:
    def test_happy_path(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko(
                {
                    "show version": SHOW_VERSION_OUTPUT,
                    "show vlan brief": SHOW_VLAN_BRIEF_OUTPUT,
                }
            ),
        )
        input_data = {"all": {"system": ["image"], "layer2": ["vlan"]}}
        result = ios_nr.run(
            task=core.generate_val_file, input_data=input_data, directory=str(tmp_path)
        )
        r = result["ios_host"][0]
        err_msg = "❌ generate_val_file: Happy path should write a val file and list used sub-features"
        assert sorted(getattr(r, "used_subfeat", [])) == ["image", "vlan"], err_msg
        assert getattr(r, "not_used_subfeat", None) == [], err_msg
        val_file = tmp_path / "ios_host_vals.yml"
        assert val_file.exists(), err_msg
        assert "vals.yml" in getattr(r, "file_info", ""), err_msg

    def test_invalid_input_marks_not_used(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko(
                {
                    "show version": SHOW_VERSION_OUTPUT,
                    "show vlan brief": "% Invalid input detected at '^' marker.",
                }
            ),
        )
        input_data = {"all": {"system": ["image"], "layer2": ["vlan"]}}
        result = ios_nr.run(
            task=core.generate_val_file, input_data=input_data, directory=str(tmp_path)
        )
        r = result["ios_host"][0]
        err_msg = "❌ generate_val_file: A device error pattern should mark the sub-feature not_used"
        assert getattr(r, "used_subfeat", None) == ["image"], err_msg
        assert getattr(r, "not_used_subfeat", None) == ["vlan"], err_msg

    def test_command_raises_handled(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        """Unlike validate, generate_val_file catches NornirSubTaskError - it isn't fatal."""
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": NornirSubTaskError(task=None, result=None)}),
        )
        input_data = {"all": {"system": ["image"]}}
        result = ios_nr.run(
            task=core.generate_val_file, input_data=input_data, directory=str(tmp_path)
        )
        r = result["ios_host"][0]
        err_msg = "❌ generate_val_file: A raising command should be handled, not fatal"
        assert not r.failed, err_msg
        assert getattr(r, "not_used_subfeat", None) == ["image"], err_msg

    def test_nothing_enabled_no_file_written(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": "% Invalid input detected at '^' marker."}),
        )
        input_data = {"all": {"system": ["image"]}}
        result = ios_nr.run(
            task=core.generate_val_file, input_data=input_data, directory=str(tmp_path)
        )
        r = result["ios_host"][0]
        err_msg = "❌ generate_val_file: No enabled sub-features should write no file and warn"
        assert getattr(r, "used_subfeat", None) == [], err_msg
        assert list(tmp_path.iterdir()) == [], err_msg
        assert "No validation file created" in getattr(r, "file_info", ""), err_msg

    def test_no_input_data_falls_back_to_all_index(
        self,
        ios_nr: Nornir,
        monkeypatch: pytest.MonkeyPatch,
        fake_netmiko: Callable[[dict[str, Any]], Callable[..., Result]],
        tmp_path: Path,
    ) -> None:
        """Omitting input_data should build validations from create_val_dm()/all_index.yml."""
        monkeypatch.setattr(
            core,
            "netmiko_send_command",
            fake_netmiko({"show version": SHOW_VERSION_OUTPUT}),
        )
        result = ios_nr.run(
            task=core.generate_val_file, input_data="", directory=str(tmp_path)
        )
        r = result["ios_host"][0]
        err_msg = "❌ generate_val_file: No input_data should validate against all_index.yml, not just nothing"
        # 'image' is enabled (has canned output), other ios sub-features have no canned command so error out
        assert "image" in getattr(r, "used_subfeat", []), err_msg
        assert len(getattr(r, "not_used_subfeat", [])) > 1, err_msg


# ----------------------------------------------------------------------------
# 4. PRINT: Smoke tests that the print helpers don't raise and emit the host name
# ----------------------------------------------------------------------------
class TestPrintResults:
    def test_print_result_val(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = AggregatedResult("validate")
        multi_result = MultiResult("validate")
        multi_result.append(
            Result(host=None, result="", report_complies="✅ True", report_file="")
        )
        result["ios_host"] = multi_result
        core.print_result_val(result)
        assert "ios_host" in capsys.readouterr().out

    def test_print_result_gvf(
        self, nr: Nornir, capsys: pytest.CaptureFixture[str]
    ) -> None:
        ios_nr = nr.filter(name="ios_host")
        result = AggregatedResult("generate_val_file")
        multi_result = MultiResult("generate_val_file")
        multi_result.append(
            Result(
                host=ios_nr.inventory.hosts["ios_host"],
                result="",
                used_subfeat=["image"],
                not_used_subfeat=[],
                file_info="✅ Validation file created",
            )
        )
        result["ios_host"] = multi_result
        core.print_result_gvf(result, ios_nr)
        assert "ios_host" in capsys.readouterr().out
