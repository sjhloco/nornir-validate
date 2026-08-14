"""These unittests test compliance_report.py: report semantics (pass/fail/skip) and file saving.

Use test_validations.py for the per-os_type report tests (built from desired_state.yml/actual_state.yml).
Use test_core.py for how validate/generate_val_file drive this module end to end.
"""

import json
import os
from pathlib import Path

import pytest

from nornir_validate import compliance_report as cr


# ----------------------------------------------------------------------------
# 1. GENERATE_VALIDATE_REPORT: Pass/fail/skip semantics, '_mode: strict' and numeric forms
# ----------------------------------------------------------------------------
class TestGenerateValidateReport:
    def test_passes(self) -> None:
        err_msg = "❌ generate_validate_report: A match should comply"
        d_state = {"system": {"image": "15.2(7)E2"}}
        a_state = {"system": {"image": "15.2(7)E2"}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["failed"] is False, err_msg
        assert report["complies"] == "✅ True", err_msg
        assert report["report"]["complies"] is True, err_msg

    def test_fails(self) -> None:
        err_msg = "❌ generate_validate_report: A mismatch should not comply and report the diff"
        d_state = {"system": {"image": "15.2(7)E2"}}
        a_state = {"system": {"image": "15.2(7)E9"}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["failed"] is True, err_msg
        assert report["complies"] == "❌ False", err_msg
        assert report["report"]["system.image"]["complies"] is False, err_msg

    def test_strict_mode_missing(self) -> None:
        err_msg = (
            "❌ generate_validate_report: '_mode: strict' should flag a missing key"
        )
        d_state = {"feat": {"sub": {"_mode": "strict", "a": 1, "b": 2}}}
        a_state = {"feat": {"sub": {"a": 1}}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["report"]["feat.sub"]["missing"] == ["b"], err_msg
        assert report["report"]["feat.sub"]["complies"] is False, err_msg

    def test_strict_mode_extra(self) -> None:
        err_msg = (
            "❌ generate_validate_report: '_mode: strict' should flag an extra key"
        )
        d_state = {"feat": {"sub": {"_mode": "strict", "a": 1}}}
        a_state = {"feat": {"sub": {"a": 1, "b": 2}}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["report"]["feat.sub"]["extra"] == ["b"], err_msg
        assert report["report"]["feat.sub"]["complies"] is False, err_msg

    @pytest.mark.parametrize(
        ("pattern", "actual", "complies"),
        [
            ("<15", 10, True),
            ("<15", 20, False),
            (">15", 20, True),
            (">15", 10, False),
            ("10<->20", 15, True),
            ("10<->20", 25, False),
            ("10%15", 16, True),
            ("10%15", 5, False),
        ],
    )
    def test_numeric_forms(self, pattern: str, actual: int, complies: bool) -> None:
        err_msg = f"❌ generate_validate_report: Numeric pattern '{pattern}' against {actual} should comply={complies}"
        d_state = {"feat": {"count": pattern}}
        a_state = {"feat": {"count": actual}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["report"]["complies"] is complies, err_msg

    def test_skipped_when_compare_not_implemented(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """NotImplementedError skip path.

        Pins current behaviour: a sub-feature whose compare() raises NotImplementedError is
        marked skipped and forces failed=True, even though 'complies' itself stays True.
        """
        err_msg = "❌ generate_validate_report: NotImplementedError should be reported as skipped"

        def fake_compare(_src: object, _dst: object) -> None:
            msg = "getter not implemented"
            raise NotImplementedError(msg)

        monkeypatch.setattr(cr.validate, "compare", fake_compare)
        d_state = {"feat": {"sub": {"a": 1}}}
        a_state = {"feat": {"sub": {"a": 1}}}
        report = cr.generate_validate_report(d_state, a_state, "host1", None)
        assert report["failed"] is True, err_msg
        assert report["report"]["skipped"] == ["feat"], err_msg
        assert report["report"]["feat"] == {
            "skipped": True,
            "reason": "NotImplemented",
        }, err_msg


# ----------------------------------------------------------------------------
# 2. FIX_HOME_PATH: napalm '~/' workaround
# ----------------------------------------------------------------------------
class TestFixHomePath:
    def test_expands_home(self) -> None:
        err_msg = "❌ _fix_home_path: '~/' should expand to the home directory"
        actual_output = cr._fix_home_path("~/reports")
        assert actual_output == os.path.expanduser("~/reports"), err_msg

    def test_leaves_absolute_path_unchanged(self) -> None:
        err_msg = "❌ _fix_home_path: An absolute path should be left untouched"
        actual_output = cr._fix_home_path("/tmp/reports")
        assert actual_output == "/tmp/reports", err_msg


# ----------------------------------------------------------------------------
# 3. SAVE_REPORT_TO_FILE: New file and merge-into-existing branches
# ----------------------------------------------------------------------------
class TestSaveReportToFile:
    def test_creates_new_file(self, tmp_path: Path) -> None:
        err_msg = "❌ _save_report_to_file: Should create a new JSON report with complies/skipped"
        cr._save_report_to_file(
            "host1", str(tmp_path), {"feat.sub": {"complies": True}}, True, []
        )
        report_files = list(tmp_path.glob("*.json"))
        assert len(report_files) == 1, err_msg
        content = json.loads(report_files[0].read_text())
        assert content == {
            "complies": True,
            "skipped": [],
            "feat.sub": {"complies": True},
        }, err_msg

    def test_merges_into_existing_file(self, tmp_path: Path) -> None:
        """A second save within the same minute (same filename) merges into the existing report."""
        err_msg = "❌ _save_report_to_file: Should merge into, not overwrite, an existing report"
        cr._save_report_to_file(
            "host1", str(tmp_path), {"feat.sub": {"complies": True}}, True, []
        )
        cr._save_report_to_file(
            "host1", str(tmp_path), {"feat.sub2": {"complies": False}}, False, []
        )
        report_files = list(tmp_path.glob("*.json"))
        assert len(report_files) == 1, err_msg
        content = json.loads(report_files[0].read_text())
        assert content["feat.sub"] == {"complies": True}, err_msg
        assert content["feat.sub2"] == {"complies": False}, err_msg
        assert content["complies"] is False, err_msg
