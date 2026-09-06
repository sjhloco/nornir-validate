from collections import defaultdict
from typing import Any, NamedTuple


# ----------------------------------------------------------------------------
# KEY: Set dictionary keys on a per-os_type basis
# ----------------------------------------------------------------------------
class OsKeys(NamedTuple):
    omp_peer: str
    cntl_nhbr: str
    cntl_color: str
    bfd_nhbr: str


def _set_keys(os_type: str) -> OsKeys:
    """Based on the OS type set the set the dictionary keys when gleaning data from NTC data structures.

    Args:
        os_type (str): A list of strings that are the OS types of the devices in the inventory
    Returns:
        OsKeys: Dictionary Keys for the specific OS type to retrieve the output data
    """
    if "ios" in os_type:  # noqa: SIM114
        return OsKeys("peer", "system_ip", "local_color", "system_ip")
    elif "viptela" in os_type:
        return OsKeys("peer", "system_ip", "remote_color", "system_ip")
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


def format_control_conn(
    val_file: bool, key: OsKeys, output: list[dict[str, str]]
) -> dict[str | int, Any]:
    """Format control connections into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        dict[str | int, Any]: {site_id: {nhbr: {colors: {color: state}}}} val file colors is a list of [color]
    """
    result: dict[str | int, dict[str, Any]] = defaultdict(dict)
    for entry in output:
        site_id = _make_int(entry["site_id"])
        nhbr = entry[key.cntl_nhbr]
        color = entry[key.cntl_color]
        nhbr_data = result[site_id].setdefault(nhbr, {})
        # Val file is a list of colors, actual state a dict of the color and its state
        if val_file:
            colors = nhbr_data.setdefault("colors", [])
            if color not in colors:
                colors.append(color)
        else:
            colors = nhbr_data.setdefault("colors", {})
            # Collapsed vbond connections must not let an up state hide an already bad one
            if colors.get(color, "up") == "up":
                colors[color] = entry["state"]
    return dict(result)


def format_omp(
    val_file: bool, key: OsKeys, output: list[dict[str, str]]
) -> dict[str, Any]:
    """Format OMP peer into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        dict[str, dict[str, str | int]]: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:x}} val file has no {state: x}
    """
    result: dict[str, dict[str, str | int]] = defaultdict(dict)
    for entry in output:
        peer = entry[key.omp_peer]
        result[peer]["site_id"] = _make_int(entry["site_id"])
        result[peer]["routes_received"] = _make_int(entry["routes_received"])
        result[peer]["routes_installed"] = _make_int(entry["routes_installed"])
        result[peer]["routes_sent"] = _make_int(entry["routes_sent"])
        # If is actual_state adds peer state
        if not val_file:
            result[peer]["state"] = entry["state"]
    return dict(result)


def format_bfd_session(
    val_file: bool, key: OsKeys, output: list[dict[str, str]]
) -> dict[str | int, Any]:
    """Format BFD sessions into the data structure.

    Args:
        val_file (bool): Used to identify if creating validation file as sometimes need implicit values
        key (OsKeys): Keys for the specific OS type to retrieve the output data
        output (list[dict[str, str]]): The command output from the device in ntc data structure OR raw data structure
    Returns:
        dict[str | int, Any]: {site_id: {nhbr: {color_pairs: {local->remote: state}}}} val file color_pairs is a list of [local->remote]
    """
    result: dict[str | int, dict[str, Any]] = defaultdict(dict)
    for entry in output:
        site_id = _make_int(entry["site_id"])
        nhbr = entry[key.bfd_nhbr]
        color_pair = f"{entry['local_color']}->{entry['remote_color']}"
        nhbr_data = result[site_id].setdefault(nhbr, {})
        # Val file is a list of color pairs, actual state a dict of the color pair and its state
        if val_file:
            nhbr_data.setdefault("color_pairs", []).append(color_pair)
        else:
            nhbr_data.setdefault("color_pairs", {})[color_pair] = entry["state"]
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
        dict[Any, Any]: Returns cmd output formatted into the data structure of actual state or validation file
    """
    key = _set_keys(os_type)
    raw_output, ntc_output = _format_output(os_type, sub_feature, output)

    ### CONTROL_CONN: {site_id: {nhbr: {colors: {color: state}}}}
    if sub_feature == "control_conn":
        return format_control_conn(val_file, key, ntc_output)
    ### OMP_PEER: {peer: {site_id:x, routes_received:x, routes_installed:x:, routes_sent:x, state:x}}
    elif sub_feature == "omp_peer":
        return format_omp(val_file, key, ntc_output)
    ### BFD_SESSION: {site_id: {nhbr: {color_pairs: {local->remote: state}}}}
    elif sub_feature == "bfd_session":
        return format_bfd_session(val_file, key, ntc_output)
    ### CatchAll
    else:
        msg = f"Unsupported sub_feature: {sub_feature}"
        raise ValueError(msg)
