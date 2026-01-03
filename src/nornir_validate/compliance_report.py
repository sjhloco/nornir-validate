import json
import os
import re
from datetime import datetime
from typing import Any

from napalm.base import validate  # type: ignore


# ----------------------------------------------------------------------------
# FIX: napalm_validate doesn't recognize ~/ for home drive
# ----------------------------------------------------------------------------
def _fix_home_path(input_path: str) -> str:
    """If the string starts with `~/`, it replaces the `~` with the user's home directory (due to napalm bug #1180).

    Arg:
        input_path (str): The path to the input file

    Return (str): The input path with the home directory expanded
    """
    if re.match("^~/", input_path):
        return os.path.expanduser(input_path)
    else:
        return input_path


# -------------------------------------------------------------------------------------------
# REPORT_FILE: If a hostname and directory are passed in as function arguments saves report to file
# --------------------------------------------------------------------------------------------
def _save_report_to_file(
    hostname: str,
    directory: str,
    report: dict[str, Any],
    complies: bool,
    skipped: list[str],
) -> str:
    """If report file exists updates the 'skipped' and 'complies' keys, else creates a report with 'skipped' and 'complies' keys.

    Args:
        hostname (str): The hostname of the device running the validation against
        directory (str): The directory where the report will be saved
        report (dict[str, Any]): The report dictionary that is returned by napalm_validate to be used by nornir Result
        complies (bool): True if the device complies with the validation rules, False otherwise
        skipped (list[str]): A list of skipped tests

    Return: Report location and command to view prettified version (xxx | python -m json.tool)
    """
    filename = os.path.join(
        _fix_home_path(directory),
        hostname
        + "_compliance_report_"
        + datetime.now().strftime("%Y%m%d-%H%M")
        + ".json",
    )
    # If report file already exists conditionally updates 'skipped' and 'complies' with report outcome
    if os.path.exists(filename):
        with open(filename) as file_content:
            existing_report = json.load(file_content)
        if list(report.values())[0].get("skipped"):
            existing_report["skipped"].extend(skipped)
        elif len(skipped) == 0:
            existing_report["skipped"] = skipped
        # Only adds if is no already failing compliance
        if existing_report.get("complies"):
            existing_report["complies"] = complies
    # If creating a new report file adds 'complies' and 'skipped' with report outcome
    else:
        existing_report = {}
        existing_report["complies"] = complies
        if len(skipped) == 0:
            existing_report["skipped"] = skipped
    # Writes to file the full napalm_validate result (including an existing report)
    existing_report.update(report)
    with open(filename, "w") as file_content:
        json.dump(existing_report, file_content)
    # return f" The report can be viewed using:  \n \33[3m\033[1;37m\33[30m  cat {filename} | python -m json.tool \033[0;0m"
    return (
        f" The full report can be viewed using 'cat {filename} | python -m json.tool'"
    )


# ----------------------------------------------------------------------------------------------------------
# VALIDATE: Uses naplam_validate on custom data fed in (still supports '_mode: strict') to validate and create reports
# ----------------------------------------------------------------------------------------------------------
def generate_validate_report(
    d_state: dict[str, Any],
    a_state: dict[str, Any],
    hostname: str,
    directory: str | None,
) -> dict[str, Any]:
    """Runs the napalm-validate compare method on each feature, adds skipped key if cant be run producing compliance report output based on all features.

    Args:
        d_state (dict[str, Any]): Desired state got from the user input
        a_state (dict[str, Any]): Actual state got from the device
        hostname (str): Hostname of the device being validated
        directory (str | None): If specified the directory where the report will be saved

    Returns (dict[str, Any]): A dictionary of report details result (compliance state) and tasks status, all all fed into Nornir Result
    """
    report: dict[str, Any] = {}
    for feature, sub_feat in d_state.items():
        for each_sub_feat in sub_feat:
            try:
                name = f"{feature}.{each_sub_feat}"
                # napalm_validate compare method produces report based on desired and actual state
                d_state_sub_feat = d_state[feature][each_sub_feat]
                a_state_sub_feat = a_state[feature][each_sub_feat]
                if isinstance(d_state_sub_feat, dict):
                    report[name] = validate.compare(d_state_sub_feat, a_state_sub_feat)
                else:
                    report[name] = validate.compare(
                        {each_sub_feat: d_state_sub_feat},
                        {each_sub_feat: a_state_sub_feat},
                    )
            # If validation couldn't be run on a command adds skipped key to the cmd dictionary
            except NotImplementedError:
                report[feature] = {"skipped": True, "reason": "NotImplemented"}
    # RESULT: Results of compliance report (complies = validation result, skipped (list of skipped cmds) = validation didn't run)
    complies = all([each_cmpl.get("complies", True) for each_cmpl in report.values()])
    skipped = [feat for feat, output in report.items() if output.get("skipped", False)]

    # REPORT_FILE: Save report to file, if not add complies and skipped dictionary to report
    if hostname is not None and directory is not None:
        report_file = _save_report_to_file(
            hostname, directory, report, complies, skipped
        )
    else:
        # Empty value if report_file not created
        report_file = ""
    # complies and skipped must be added after the report
    report["complies"] = complies
    if len(skipped) != 0:
        report["skipped"] = skipped
    # RETURN_RESULT: If compliance fails set state failed (used by Nornir)
    if complies:
        my_report = dict(
            failed=False, report=report, report_file=report_file, complies="✅ True"
        )
    if not complies or skipped:
        my_report = dict(
            failed=True, report=report, report_file=report_file, complies="❌ False"
        )
    return my_report
