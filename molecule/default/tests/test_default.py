"""Molecule testinfra tests for ansible-role-kea-dhcp.

These tests verify the converged state of the role on Ubuntu Resolute (26.04 LTS)
with kea_dhcp4_enabled: true and the minimal test subnet from converge.yml.

They are integration tests — they inspect real filesystem state, package
state, systemd service status, and rendered config content on the test instance.

Config file note: the native kea-dhcp4 apt package expects its config at
/etc/kea/kea-dhcp4.conf.  The role renders templates to that path
(kea_base_dir defaults to /etc/kea).

Templates must produce standard JSON (no C-style // comments) so that
Python's json module can parse the rendered output for structured assertions.

Run during molecule verify:
    molecule verify
Or as part of the full test sequence:
    molecule test
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from testinfra.host import Host

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

JsonDict = dict[str, Any]
JsonList = list[Any]

# ---------------------------------------------------------------------------
# Constants — must match defaults/main.yml and molecule/default/converge.yml
# ---------------------------------------------------------------------------

CONF_PATH: str = "/etc/kea/kea-dhcp4.conf"
KEA_BASE_DIR: str = "/etc/kea"
LEASE_DIR: str = "/var/lib/kea"

VALID_LIFETIME: int = 6000
RENEW_TIMER: int = 3000       # valid_lifetime * 0.5
REBIND_TIMER: int = 5100      # valid_lifetime * 0.85
PARKED_PACKET_LIMIT: int = 128
LOG_SEVERITY: str = "INFO"

TEST_SUBNET: str = "192.0.2.0/24"
TEST_POOL_START: str = "192.0.2.100"
TEST_POOL_END: str = "192.0.2.200"
TEST_SUBNET_ID: int = 1

# External reservation files — merge_reservations.yml (see
# molecule/default/prepare.yml and converge.yml's kea_dhcp4_subnets fixture).
RESERVATIONS_DIR: str = "/etc/kea/reservations"
RESERVATIONS_PRESEEDED_FILE: str = f"{RESERVATIONS_DIR}/printers.json"
RESERVATIONS_PLACEHOLDER_FILE: str = f"{RESERVATIONS_DIR}/generic-hosts.json"
EXPECTED_EXTERNAL_RESERVATIONS: JsonList = [
    {
        "hostname": "printer-002",
        "hw-address": "14:58:d0:40:f1:28",
        "ip-address": "192.0.2.12",
    },
    {
        "hostname": "printer-003",
        "hw-address": "f0:4e:a4:07:6b:74",
        "ip-address": "192.0.2.13",
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json_config(host: Host, path: str) -> JsonDict:
    """Read a Kea JSON config file from the host and return parsed content.

    Delegates parsing to python3 on the test instance so that the host's
    json module is used.  The rendered config must be standard JSON — no
    C-style comments — for this helper to succeed.

    Args:
        host: The testinfra host fixture.
        path: Absolute path to the JSON config file on the host.

    Returns:
        Parsed config as a dict.

    Raises:
        AssertionError: If python3 cannot parse the file as JSON.
    """
    result = host.run(
        f"python3 -c \"import json, sys; "
        f"print(json.dumps(json.load(open('{path}'))))\" 2>&1"
    )
    assert result.rc == 0, f"{path} is not valid JSON:\n{result.stdout}"
    parsed: JsonDict = json.loads(result.stdout)
    return parsed


def get_dhcp4(host: Host) -> JsonDict:
    """Return the Dhcp4 top-level object from the rendered config.

    Args:
        host: The testinfra host fixture.

    Returns:
        The value of the top-level ``Dhcp4`` key.
    """
    cfg = load_json_config(host, CONF_PATH)
    assert "Dhcp4" in cfg, f"Missing top-level 'Dhcp4' key in {CONF_PATH}"
    dhcp4: JsonDict = cfg["Dhcp4"]
    return dhcp4


# ---------------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------------


def test_kea_dhcp4_package_installed(host: Host) -> None:
    """kea-dhcp4 must be present after role converge."""
    assert host.package("kea-dhcp4").is_installed


def test_kea_common_package_installed(host: Host) -> None:
    """kea-common is a shared dependency pulled in by kea-dhcp4."""
    assert host.package("kea-common").is_installed


@pytest.mark.parametrize(
    "pkg",
    [
        "kea-dhcp6",
        "kea-ctrl-agent",
        "kea-dhcp-ddns",
    ],
)
def test_disabled_service_packages_absent(host: Host, pkg: str) -> None:
    """Packages for services disabled in converge.yml must not be installed."""
    assert not host.package(pkg).is_installed, (
        f"{pkg} should not be installed when its service is disabled"
    )


# ---------------------------------------------------------------------------
# System identity — _kea user and group
# ---------------------------------------------------------------------------


def test_kea_group_exists(host: Host) -> None:
    """The _kea system group must be created by the kea-common package."""
    assert host.group("_kea").exists


def test_kea_user_exists(host: Host) -> None:
    """The _kea system user must be created by the kea-common package."""
    assert host.user("_kea").exists


def test_kea_user_is_system_account(host: Host) -> None:
    """_kea must be a system (non-login) account with uid < 1000."""
    uid: int = host.user("_kea").uid
    assert uid < 1000, f"_kea uid {uid} looks like a regular user account"


def test_kea_user_in_kea_group(host: Host) -> None:
    """_kea user must be a member of the _kea group."""
    assert "_kea" in host.user("_kea").groups


# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        KEA_BASE_DIR,
        LEASE_DIR,
    ],
)
def test_kea_directory_exists(host: Host, path: str) -> None:
    """Required Kea directories must exist after role converge."""
    d = host.file(path)
    assert d.exists, f"{path} does not exist"
    assert d.is_directory, f"{path} is not a directory"


# ---------------------------------------------------------------------------
# Config file — presence, ownership, permissions
# ---------------------------------------------------------------------------


def test_config_file_exists(host: Host) -> None:
    assert host.file(CONF_PATH).exists
    assert host.file(CONF_PATH).is_file


def test_config_file_mode(host: Host) -> None:
    """Config must be readable by root and the _kea group only (0640)."""
    assert host.file(CONF_PATH).mode == 0o640, (
        f"{CONF_PATH} mode is {oct(host.file(CONF_PATH).mode)}, expected 0o640"
    )


def test_config_file_group(host: Host) -> None:
    """Config must be group-owned by _kea so the service can read it."""
    assert host.file(CONF_PATH).group == "_kea", (
        f"{CONF_PATH} group is {host.file(CONF_PATH).group!r}, expected '_kea'"
    )


def test_config_file_no_unrendered_jinja(host: Host) -> None:
    """No Jinja2 template expressions may appear in the rendered config."""
    content: str = host.file(CONF_PATH).content_string
    assert "{{" not in content, "Unrendered Jinja opening tag found in config"
    assert "}}" not in content, "Unrendered Jinja closing tag found in config"


def test_config_file_no_include_directives(host: Host) -> None:
    """Kea <?include?> directives must be replaced by inlined content.

    The docker-era templates used <?include "/kea/config/subnet4.json"?>.
    The native-apt templates must inline subnet content directly so the
    rendered file is a single valid JSON document.
    """
    content: str = host.file(CONF_PATH).content_string
    assert "<?include" not in content, (
        "Kea <?include?> directive found — template must inline subnet content"
    )


def test_config_is_valid_json(host: Host) -> None:
    """The rendered config must parse as standard JSON without errors."""
    load_json_config(host, CONF_PATH)  # raises AssertionError on failure


# ---------------------------------------------------------------------------
# Config structure — top-level keys
# ---------------------------------------------------------------------------


def test_config_has_dhcp4_key(host: Host) -> None:
    """The rendered config must have a top-level 'Dhcp4' key."""
    cfg = load_json_config(host, CONF_PATH)
    assert "Dhcp4" in cfg


def test_config_no_control_socket(host: Host) -> None:
    """No control-socket when kea_ctrl_agent_enabled is false."""
    dhcp4 = get_dhcp4(host)
    assert "control-socket" not in dhcp4, (
        "control-socket must not appear when kea_ctrl_agent_enabled is false"
    )


def test_config_no_dhcp_ddns(host: Host) -> None:
    """No dhcp-ddns block when kea_ddns_enabled is false."""
    dhcp4 = get_dhcp4(host)
    assert "dhcp-ddns" not in dhcp4, (
        "dhcp-ddns must not appear when kea_ddns_enabled is false"
    )


# ---------------------------------------------------------------------------
# Config content — interfaces
# ---------------------------------------------------------------------------


def test_config_interfaces_present(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert "interfaces-config" in dhcp4


def test_config_interfaces_wildcard(host: Host) -> None:
    """Default kea_dhcp_interfaces is ['*'] — must appear in rendered config."""
    dhcp4 = get_dhcp4(host)
    interfaces: JsonList = dhcp4["interfaces-config"]["interfaces"]
    assert "*" in interfaces, (
        f"Expected '*' in interfaces, got {interfaces!r}"
    )


# ---------------------------------------------------------------------------
# Config content — lease database
# ---------------------------------------------------------------------------


def test_config_lease_database_present(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert "lease-database" in dhcp4


def test_config_lease_database_type_memfile(host: Host) -> None:
    """Lease database must use the memfile backend (no external DB required)."""
    dhcp4 = get_dhcp4(host)
    assert dhcp4["lease-database"]["type"] == "memfile", (
        f"Expected memfile, got {dhcp4['lease-database']['type']!r}"
    )


# ---------------------------------------------------------------------------
# Config content — timers and limits (from defaults/main.yml)
# ---------------------------------------------------------------------------


def test_config_valid_lifetime(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert dhcp4["valid-lifetime"] == VALID_LIFETIME, (
        f"valid-lifetime is {dhcp4['valid-lifetime']}, expected {VALID_LIFETIME}"
    )


def test_config_renew_timer(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert dhcp4["renew-timer"] == RENEW_TIMER, (
        f"renew-timer is {dhcp4['renew-timer']}, expected {RENEW_TIMER}"
    )


def test_config_rebind_timer(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert dhcp4["rebind-timer"] == REBIND_TIMER, (
        f"rebind-timer is {dhcp4['rebind-timer']}, expected {REBIND_TIMER}"
    )


def test_config_parked_packet_limit(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert dhcp4["parked-packet-limit"] == PARKED_PACKET_LIMIT, (
        f"parked-packet-limit is {dhcp4['parked-packet-limit']}, "
        f"expected {PARKED_PACKET_LIMIT}"
    )


# ---------------------------------------------------------------------------
# Config content — multi-threading
# ---------------------------------------------------------------------------


def test_config_multi_threading_present(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert "multi-threading" in dhcp4


def test_config_multi_threading_enabled(host: Host) -> None:
    """kea_dhcp_multi_threading_enable defaults to true."""
    dhcp4 = get_dhcp4(host)
    assert dhcp4["multi-threading"]["enable-multi-threading"] is True


# ---------------------------------------------------------------------------
# Config content — logging
# ---------------------------------------------------------------------------


def test_config_loggers_present(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert "loggers" in dhcp4
    loggers: JsonList = dhcp4["loggers"]
    assert len(loggers) > 0, "loggers list must not be empty"


def test_config_logging_severity(host: Host) -> None:
    """Default kea_logging_severity is INFO."""
    dhcp4 = get_dhcp4(host)
    loggers: JsonList = dhcp4["loggers"]
    for logger in loggers:
        assert logger["severity"] == LOG_SEVERITY, (
            f"Logger {logger.get('name')!r} severity is "
            f"{logger['severity']!r}, expected {LOG_SEVERITY!r}"
        )


# ---------------------------------------------------------------------------
# Config content — subnets (from converge.yml)
# ---------------------------------------------------------------------------


def test_config_subnet4_present(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    assert "subnet4" in dhcp4
    assert len(dhcp4["subnet4"]) > 0, "subnet4 list must not be empty"


def test_config_subnet4_count(host: Host) -> None:
    """converge.yml defines exactly one subnet."""
    dhcp4 = get_dhcp4(host)
    assert len(dhcp4["subnet4"]) == 1, (
        f"Expected 1 subnet, found {len(dhcp4['subnet4'])}"
    )


def test_config_subnet4_cidr(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    subnets: JsonList = dhcp4["subnet4"]
    cidrs: list[str] = [s["subnet"] for s in subnets]
    assert TEST_SUBNET in cidrs, (
        f"Expected subnet {TEST_SUBNET!r} not found in {cidrs!r}"
    )


def test_config_subnet4_id_is_integer(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    for subnet in dhcp4["subnet4"]:
        assert isinstance(subnet["id"], int), (
            f"Subnet {subnet.get('subnet')!r} id is not an integer: "
            f"{subnet['id']!r}"
        )


def test_config_subnet4_ids_unique(host: Host) -> None:
    """Subnet IDs must be unique — Kea rejects duplicates at startup."""
    dhcp4 = get_dhcp4(host)
    ids: list[int] = [s["id"] for s in dhcp4["subnet4"]]
    assert len(ids) == len(set(ids)), f"Duplicate subnet IDs found: {ids!r}"


def test_config_subnet4_has_pools(host: Host) -> None:
    dhcp4 = get_dhcp4(host)
    for subnet in dhcp4["subnet4"]:
        pools: JsonList = subnet.get("pools", [])
        assert len(pools) > 0, (
            f"Subnet {subnet.get('subnet')!r} has no pools defined"
        )


def test_config_subnet4_pool_range(host: Host) -> None:
    """Test pool from converge.yml must appear in rendered pools."""
    dhcp4 = get_dhcp4(host)
    all_pools: list[str] = [
        p["pool"]
        for subnet in dhcp4["subnet4"]
        for p in subnet.get("pools", [])
    ]
    expected_pool = f"{TEST_POOL_START} - {TEST_POOL_END}"
    assert any(TEST_POOL_START in p and TEST_POOL_END in p for p in all_pools), (
        f"Expected pool {expected_pool!r} not found in rendered pools: "
        f"{all_pools!r}"
    )


# ---------------------------------------------------------------------------
# Config content — external reservation files (merge_reservations.yml)
# ---------------------------------------------------------------------------


def test_reservations_dir_exists(host: Host) -> None:
    d = host.file(RESERVATIONS_DIR)
    assert d.exists, f"{RESERVATIONS_DIR} does not exist"
    assert d.is_directory, f"{RESERVATIONS_DIR} is not a directory"


def test_reservations_dir_owner_and_mode(host: Host) -> None:
    d = host.file(RESERVATIONS_DIR)
    assert d.user == "_kea", f"{RESERVATIONS_DIR} owner is {d.user!r}, expected '_kea'"
    assert d.group == "_kea", f"{RESERVATIONS_DIR} group is {d.group!r}, expected '_kea'"
    assert d.mode == 0o750, f"{RESERVATIONS_DIR} mode is {oct(d.mode)}, expected 0o750"


def test_preseeded_reservation_file_ownership_reconciled(host: Host) -> None:
    """prepare.yml seeds printers.json before _kea exists; the role must
    still reconcile ownership to _kea:_kea without touching its content."""
    f = host.file(RESERVATIONS_PRESEEDED_FILE)
    assert f.exists
    assert f.user == "_kea"
    assert f.group == "_kea"
    assert f.mode == 0o640


def test_preseeded_reservation_file_content_untouched(host: Host) -> None:
    """force: false must not overwrite content already deployed on disk."""
    content = json.loads(host.file(RESERVATIONS_PRESEEDED_FILE).content_string)
    assert content == EXPECTED_EXTERNAL_RESERVATIONS


def test_missing_reservation_file_gets_placeholder(host: Host) -> None:
    """generic-hosts.json is listed but never pre-seeded — the role must
    create an empty, valid placeholder rather than failing config render."""
    f = host.file(RESERVATIONS_PLACEHOLDER_FILE)
    assert f.exists
    assert f.user == "_kea"
    assert f.group == "_kea"
    assert f.mode == 0o640
    assert json.loads(f.content_string) == []


def test_config_subnet4_reservations_merged_from_external_files(host: Host) -> None:
    """subnet4[0].reservations must contain exactly the entries contributed
    by printers.json; generic-hosts.json contributes nothing (empty placeholder)."""
    dhcp4 = get_dhcp4(host)
    subnet = next(s for s in dhcp4["subnet4"] if s["id"] == TEST_SUBNET_ID)
    assert subnet.get("reservations") == EXPECTED_EXTERNAL_RESERVATIONS


def test_config_subnet4_has_no_reservation_files_key(host: Host) -> None:
    """reservation_files is an Ansible role directive, not a Kea subnet4
    parameter — it must never leak into the rendered config."""
    dhcp4 = get_dhcp4(host)
    for subnet in dhcp4["subnet4"]:
        assert "reservation_files" not in subnet, (
            f"Subnet {subnet.get('subnet')!r} leaked a reservation_files key "
            "into the rendered Kea config"
        )


# ---------------------------------------------------------------------------
# Systemd service — kea-dhcp4
# ---------------------------------------------------------------------------


def test_kea_dhcp4_service_enabled(host: Host) -> None:
    assert host.service("kea-dhcp4").is_enabled


def test_kea_dhcp4_service_running(host: Host) -> None:
    assert host.service("kea-dhcp4").is_running
