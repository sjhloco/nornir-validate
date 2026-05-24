import re
from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    intf_name: str
    intf_type: str
    intf_status: str
    ip_name: str
    ip_ip: str
    ip_status: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:
        return OsKeys("port", "vlan_id", "status", "interface", "ip_address", "status")
    elif "nxos" in os_type:
        return OsKeys("port", "vlan_id", "status", "intf-name", "prefix", "link-state")
    elif "asa" in os_type:
        return OsKeys(
            "interface",
            "interface_zone",
            "link_status",
            "interface",
            "ip_address",
            "status",
        )
    elif "wlc" in os_type:
        return OsKeys(
            "port", "stp_status", "link_status", "name", "ip_address", "status"
        )
    elif "panos" in os_type:
        return OsKeys("interface", "", "state", "interface", "ip_address", "state")
    # Fallback if nothing matched
    msg = f"Error, '_set_keys' has no match for OS type: '{os_type}'"
    raise NotImplementedError(msg)


# ----------------------------------------------------------------------------
# OUTPUT: Creates str or ntc output dictionaries based on device command output
# ----------------------------------------------------------------------------
def _format_output(
    os_type: str, sub_feature: str, output: list[str | dict[str, str]]
) -> tuple[list[str], list[dict[str, str]]]:
    """Screen scraping return different data structures, they need defining to make function typing easier.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str from raw) command output from the device
    Raises:
        ValueError: Errors if the new output variable doesn't match the input as not meant to be changing it, just defining it for MYPY
    Returns:
        tuple[list[str], list[dict[str, str]]]: Returns either RAW list[str] or NTC list[dict], the other non-matched one will be empty
    """
    raw_output = [o for o in output if isinstance(o, str)]
    ntc_output = [o for o in output if isinstance(o, dict)]
    if (
        len(raw_output) != 0
        and output != raw_output
        or len(ntc_output) != 0
        and output != ntc_output
    ):
        msg = f"{os_type} {sub_feature} _format_output is malformed"
        raise ValueError(msg)
    return raw_output, ntc_output


# ----------------------------------------------------------------------------
# DEF: Mini-functions used by the main function
# ----------------------------------------------------------------------------
def _make_int(input_data: str) -> int | str:
    """Takes a string and returns an integer if it can, otherwise it returns the original string.

    Args:
        input_data (str): The data to be converted to an integer
    Returns:
        int | str: The input_data as a integer if possible, if not as the original string
    """
    try:
        return int(input_data)
    except ValueError:
        return input_data


def _fix_nxos(
    main_dict: dict[str, Any], parent_name: str, child_name: str
) -> list[dict[str, Any]]:
    """NXOS JSON makes dict rather than list if only 1 item in output. If the child_dict is a dict this methods convert it to a list.

    Args:
        main_dict (dict[str, Any]): The dictionary of the command output
        parent_name (str): The parent dictionary key name (e.g. TABLE_xx)
        child_name (str): The key of the dictionary that you want to fix, for example ROW_xx
    Returns:
        A list of dictionaries
    """
    child_dict_value: list[dict[str, Any]] | dict[str, Any] = main_dict[parent_name][
        child_name
    ]
    if isinstance(child_dict_value, dict):
        child_dict_value = [child_dict_value]
    return child_dict_value


def _make_none(
    input_dict: dict[str, str | int | None], dict_key: str
) -> str | int | None:
    """Checks dict key value and if empty returns None.

    Args:
        input_dict(dict[str, str | int | None]): Input dictionary of key-value pairs
        dict_key(key): The dict key that want to check
    Returns:
        str | int | None: The key value or if empty None
    """
    tmp_value = input_dict.get(dict_key, "")
    if tmp_value is None:
        return None
    if isinstance(tmp_value, str):
        return tmp_value if tmp_value else None
    return tmp_value  # keep int values as-is


def format_intf(
    val_file: bool, os_type: str, key: OsKeys, output: list[dict[str, Any]]
) -> dict[str | int, Any]:
    """Format interface output into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str | int, Any]:  {intf: {duplex: x, speed: x, type:x, status: connected }}, val_file doesn't have 'status'
    """
    result: dict[str | int, dict[str, str | int | None]] = defaultdict(dict)
    skip_statuses = {
        "disabled",
        "xcvrAbsen",
        "administratively down",
        "admin down",
        "Down",
        "notconnec",
        "notconnect",
        "down",
    }
    for each_intf in output:
        intf_name = _make_int(each_intf[key.intf_name])
        # BYPASS: Dont include disabled ports when building val_file
        if val_file and each_intf[key.intf_status] in skip_statuses:
            continue
        # SPEED/DUPLEX: WLC doesnt have standard duplex and speed NTC keys
        if bool(re.search("wlc", os_type)):
            result[intf_name]["speed"] = _make_int(
                each_intf["physical_status"].split()[0]
            )
            try:
                duplex = _make_int(each_intf["physical_status"].split()[1])
                result[intf_name]["duplex"] = duplex
            except IndexError:
                result[intf_name]["duplex"] = each_intf["physical_status"]
        # SPEED/DUPLEX: actual file
        elif not val_file:
            result[intf_name]["duplex"] = _make_none(each_intf, "duplex")
            result[intf_name]["speed"] = _make_int(each_intf["speed"])
            result[intf_name]["speed"] = _make_none(result[intf_name], "speed")
        # SPEED/DUPLEX: Val file
        elif val_file:
            if len(each_intf["duplex"]) != 0:
                result[intf_name]["duplex"] = each_intf["duplex"]
            if len(each_intf["speed"]) != 0:
                result[intf_name]["speed"] = _make_int(each_intf["speed"])
        # TYPE: Applies to actual_state and val_file
        if isinstance(_make_int(each_intf.get(key.intf_type, "x")), int):
            result[intf_name]["type"] = "access"
        # TYPE: Actual_state only
        elif not val_file:
            result[intf_name]["type"] = _make_none(each_intf, key.intf_type)
        # TYPE: VAL_file only
        elif len(each_intf.get(key.intf_type, "")) != 0:
            result[intf_name]["type"] = each_intf[key.intf_type]
        # STATUS: Applies all Actual_state
        if not val_file:
            result[intf_name]["status"] = (
                each_intf[key.intf_status].lower().replace("up", "connected")
            )
    return dict(result)


def format_swport(val_file: bool, output: list[dict[str, Any]]) -> dict[str, Any]:
    """Format switchport output into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]:  {intf: {mode: access or trunk, vlan: x or [x,y]}}
    """
    result: dict[str, dict[str, str | int | list[str] | None]] = defaultdict(dict)

    for each_intf in output:
        # BYPASS: Dont include disabled ports when building val_file
        skip_statuses = {"down", ""}
        if val_file and each_intf["mode"] in skip_statuses:
            continue
        if len(each_intf["mode"]) == 0:
            continue
        else:
            mode = each_intf["mode"].replace("static ", "").split()[0]
        result[each_intf["interface"]]["mode"] = mode
        if each_intf["mode"] == "static access" or each_intf["mode"] == "access":
            result[each_intf["interface"]]["vlan"] = _make_int(each_intf["access_vlan"])
        elif bool(re.search("trunk", each_intf["mode"])):
            trunk_vl = each_intf["trunking_vlans"]
            # If is a string (NXOS) split into list of VLANs based on ","
            if isinstance(trunk_vl, str):
                trunk_vl = [_make_int(vl) for vl in trunk_vl.split(",")]
            # If is already a list of VLANs (IOS), if possible make them integers
            elif isinstance(trunk_vl, list):
                trunk_vl = [_make_int(vl) for vl in trunk_vl]
            else:
                trunk_vl = None
            result[each_intf["interface"]]["vlan"] = trunk_vl
        else:
            result[each_intf["interface"]]["vlan"] = None
    return dict(result)


def format_ipbrief(
    val_file: bool, os_type: str, key: OsKeys, output: list[dict[str, Any]]
) -> dict[str, Any]:
    """Format ip interface brief output into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, Any]]): The command output from the device in ntc data structure
    Returns:
        dict[str, Any]: {intf: {ip:x, status: x}}, val_file is {intfx: ipx, intfy: ipy}
    """
    result: dict[str, Any] = defaultdict(dict)
    skip_conditions = {
        key.ip_ip: ["unassigned", "N/A"],
        key.ip_status: ["administratively down", "admin-down"],
    }
    if bool(re.search("nxos", os_type)):
        output = _fix_nxos(output[0], "TABLE_intf", "ROW_intf")
    for each_intf in output:
        # Val file only
        if val_file:
            if any(
                each_intf.get(field) in values
                for field, values in skip_conditions.items()
            ):
                continue
            else:
                # As palo gets state from intf cmd, needed to stop IP from being wiped
                if (
                    bool(re.search("panos", os_type))
                    and each_intf.get(key.ip_ip) is None
                ):
                    pass
                else:
                    result[each_intf[key.ip_name]] = each_intf.get(
                        key.ip_ip, each_intf.get("unnum-intf")
                    )
        # Actual state only
        elif not val_file:
            # As palo gets state from intf cmd, needed to stop IP from being wiped
            if bool(re.search("panos", os_type)) and each_intf.get(key.ip_ip) is None:
                pass
            else:
                result[each_intf[key.ip_name]]["ip"] = each_intf.get(
                    key.ip_ip, each_intf.get("unnum-intf")
                )
            result[each_intf[key.ip_name]]["status"] = each_intf.get(
                key.ip_status, "up"
            )
    return dict(result)


# ----------------------------------------------------------------------------
# ACTUAL_STATE: Engine use to create sub-feature actual state or validation file
# ----------------------------------------------------------------------------
def format_actual_state(
    val_file: bool,
    os_type: str,
    sub_feature: str,
    output: list[str | dict[str, str]],
) -> dict[Any, Any]:
    """Engine to run all the actual state and validation file sub-feature formatting.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        os_type (str): The different Nornir platforms which are OS type of the device
        sub_feature (str): The name of the sub-feature that is being validated
        output (list[str | dict[str, str]]): The structured (dict from NTC template) or unstructured (str/int from raw) command output from the device
    Returns:
        dict[str | int, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    aw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### INTF: {intf: {duplex: x, speed: x, type:x, connected }}
    if sub_feature == "intf":
        return format_intf(val_file, os_type, key, ntc_output)
    ### SWITCHPORT: {intf: {mode: access or trunk, vlan: x or [x,y]}}
    elif sub_feature == "switchport":
        return format_swport(val_file, ntc_output)
    ### IP_BRIEF: {intf: {ip:x, status: x}}}
    elif sub_feature == "ip_brief":
        return format_ipbrief(val_file, os_type, key, ntc_output)
    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
