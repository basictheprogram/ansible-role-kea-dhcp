"""Molecule testinfra tests for the ddns scenario.

Exercises two things in combination:

1. key_management.yml — reads BIND-format TSIG key files from /etc/bind/,
   extracts the raw base64 secret, and writes it to kea_base_dir.  The
   prepare.yml for this scenario creates mock key files with known secrets
   so the extracted content can be asserted exactly.

2. deploy_ddns.yml — installs kea-dhcp-ddns-server, applies the LP #2121327
   AppArmor workaround, renders kea-dhcp-ddns.conf, and starts the service.

Scenario context (must match molecule/ddns/prepare.yml and converge.yml):
  - Mock TSIG key file : /etc/bind/d2.sha512.key
  - Mock rndc key file : /etc/bind/rndc.key  (must NOT be copied to /etc/kea/)
  - Expected secret    : MOCK_TSIG_SECRET (see constant below)
  - DNS zone           : example.test. / 2.0.192.in-addr.arpa.
  - DNS server         : 127.0.0.1:53

Run during molecule verify:
    molecule verify -s ddns
Or as part of the full test sequence:
    molecule test -s ddns
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
# Constants — must match molecule/ddns/prepare.yml and converge.yml
# ---------------------------------------------------------------------------

KEA_BASE_DIR: str = "/etc/kea"
DDNS_CONF_PATH: str = "/etc/kea/kea-dhcp-ddns.conf"
APPARMOR_OVERRIDE_PATH: str = "/etc/apparmor.d/local/usr.sbin.kea-dhcp-ddns"

# Secret written into /etc/bind/d2.sha512.key by prepare.yml.
# key_management.yml must extract this value (and only this value) into
# /etc/kea/d2.sha512.key.
MOCK_TSIG_SECRET: str = "dGVzdC10c2lnLXNlY3JldC1mb3ItbW9sZWN1bGU="

TSIG_KEY_NAME: str = "d2.sha512.key"
SECRET_FILE_PATH: str = f"{KEA_BASE_DIR}/{TSIG_KEY_NAME}"

# rndc.key in /etc/bind/ must never be copied to /etc/kea/.
RNDC_DEST_PATH: str = f"{KEA_BASE_DIR}/rndc.key"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json_config(host: Host, path: str) -> JsonDict:
    """Read a Kea JSON config file from the host and return parsed content.

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


def get_dhcpddns(host: Host) -> JsonDict:
    """Return the DhcpDdns top-level object from the rendered DDNS config.

    Args:
        host: The testinfra host fixture.

    Returns:
        The value of the top-level ``DhcpDdns`` key.
    """
    cfg = load_json_config(host, DDNS_CONF_PATH)
    assert "DhcpDdns" in cfg, f"Missing top-level 'DhcpDdns' key in {DDNS_CONF_PATH}"
    ddns: JsonDict = cfg["DhcpDdns"]
    return ddns


# ---------------------------------------------------------------------------
# key_management.yml — TSIG key extraction
# ---------------------------------------------------------------------------


def test_secret_file_exists(host: Host) -> None:
    """key_management.yml must create the secret file in kea_base_dir."""
    assert host.file(SECRET_FILE_PATH).exists, (
        f"Secret file {SECRET_FILE_PATH} was not created by key_management.yml"
    )


def test_secret_file_is_regular_file(host: Host) -> None:
    assert host.file(SECRET_FILE_PATH).is_file


def test_secret_file_mode(host: Host) -> None:
    """Secret file must be readable only by root and the _kea group (0640)."""
    assert host.file(SECRET_FILE_PATH).mode == 0o640, (
        f"{SECRET_FILE_PATH} mode is "
        f"{oct(host.file(SECRET_FILE_PATH).mode)}, expected 0o640"
    )


def test_secret_file_owner_root(host: Host) -> None:
    """Secret file must be owned by root."""
    assert host.file(SECRET_FILE_PATH).user == "root", (
        f"{SECRET_FILE_PATH} owner is "
        f"{host.file(SECRET_FILE_PATH).user!r}, expected 'root'"
    )


def test_secret_file_group_kea(host: Host) -> None:
    """Secret file must be group-owned by _kea so kea-dhcp-ddns can read it."""
    assert host.file(SECRET_FILE_PATH).group == "_kea", (
        f"{SECRET_FILE_PATH} group is "
        f"{host.file(SECRET_FILE_PATH).group!r}, expected '_kea'"
    )


def test_secret_file_content_matches_mock_secret(host: Host) -> None:
    """Extracted secret must exactly match the value from the mock key file.

    key_management.yml applies a regex to strip the BIND key stanza and
    leave only the raw base64 secret.  The content of /etc/kea/d2.sha512.key
    must equal MOCK_TSIG_SECRET (with optional trailing newline).
    """
    content: str = host.file(SECRET_FILE_PATH).content_string.strip()
    assert content == MOCK_TSIG_SECRET, (
        f"Extracted secret {content!r} does not match "
        f"expected {MOCK_TSIG_SECRET!r}"
    )


def test_secret_file_no_bind_syntax(host: Host) -> None:
    """Secret file must contain raw base64 only — no BIND key stanza syntax.

    kea-dhcp-ddns reads the secret-file value directly as a base64 string.
    Any remaining BIND syntax (key name, algorithm, braces) causes a fatal
    parse error at startup.
    """
    content: str = host.file(SECRET_FILE_PATH).content_string
    for forbidden in ("key ", "algorithm", "secret ", "{", "}"):
        assert forbidden not in content, (
            f"BIND key syntax {forbidden!r} found in {SECRET_FILE_PATH}; "
            "key_management.yml regex did not strip the stanza correctly"
        )


def test_rndc_key_not_copied(host: Host) -> None:
    """rndc.key must be excluded — it is BIND's control key, not a TSIG key.

    key_management.yml uses 'excludes: rndc.key' in the find task.  If that
    exclusion is missing, /etc/kea/rndc.key will exist and Kea will be
    misconfigured.
    """
    assert not host.file(RNDC_DEST_PATH).exists, (
        f"{RNDC_DEST_PATH} exists — rndc.key was copied but must be excluded"
    )


# ---------------------------------------------------------------------------
# kea-dhcp-ddns package
# ---------------------------------------------------------------------------


def test_kea_ddns_package_installed(host: Host) -> None:
    """kea-dhcp-ddns-server must be present after role converge."""
    assert host.package("kea-dhcp-ddns").is_installed


# ---------------------------------------------------------------------------
# DDNS config file — presence, ownership, permissions
# ---------------------------------------------------------------------------


def test_ddns_config_file_exists(host: Host) -> None:
    assert host.file(DDNS_CONF_PATH).exists
    assert host.file(DDNS_CONF_PATH).is_file


def test_ddns_config_file_mode(host: Host) -> None:
    """DDNS config must be readable by root and the _kea group only (0640)."""
    assert host.file(DDNS_CONF_PATH).mode == 0o640, (
        f"{DDNS_CONF_PATH} mode is "
        f"{oct(host.file(DDNS_CONF_PATH).mode)}, expected 0o640"
    )


def test_ddns_config_file_group(host: Host) -> None:
    assert host.file(DDNS_CONF_PATH).group == "_kea"


def test_ddns_config_no_unrendered_jinja(host: Host) -> None:
    """No Jinja2 template expressions may appear in the rendered config."""
    content: str = host.file(DDNS_CONF_PATH).content_string
    assert "{{" not in content, "Unrendered Jinja opening tag found in DDNS config"
    assert "}}" not in content, "Unrendered Jinja closing tag found in DDNS config"


def test_ddns_config_is_valid_json(host: Host) -> None:
    """The rendered DDNS config must parse as standard JSON without errors."""
    load_json_config(host, DDNS_CONF_PATH)


# ---------------------------------------------------------------------------
# DDNS config structure
# ---------------------------------------------------------------------------


def test_ddns_config_has_dhcpddns_key(host: Host) -> None:
    """Top-level key must be 'DhcpDdns' — not 'Dhcp4' or 'DhcpDdns'."""
    cfg = load_json_config(host, DDNS_CONF_PATH)
    assert "DhcpDdns" in cfg


def test_ddns_config_tsig_keys_present(host: Host) -> None:
    """tsig-keys list must contain at least one entry."""
    ddns = get_dhcpddns(host)
    assert "tsig-keys" in ddns, "Missing 'tsig-keys' in DhcpDdns config"
    keys: JsonList = ddns["tsig-keys"]
    assert len(keys) > 0, "tsig-keys list must not be empty"


def test_ddns_config_tsig_key_name(host: Host) -> None:
    """The TSIG key name must match the filename from converge.yml."""
    ddns = get_dhcpddns(host)
    key_names: list[str] = [k["name"] for k in ddns.get("tsig-keys", [])]
    assert TSIG_KEY_NAME in key_names, (
        f"Expected TSIG key {TSIG_KEY_NAME!r} not found in tsig-keys: "
        f"{key_names!r}"
    )


def test_ddns_config_tsig_secret_file_path(host: Host) -> None:
    """secret-file must point to the path that key_management.yml wrote."""
    ddns = get_dhcpddns(host)
    keys: JsonList = ddns.get("tsig-keys", [])
    target = next((k for k in keys if k.get("name") == TSIG_KEY_NAME), None)
    assert target is not None, f"TSIG key {TSIG_KEY_NAME!r} not found"
    assert target.get("secret-file") == SECRET_FILE_PATH, (
        f"secret-file is {target.get('secret-file')!r}, "
        f"expected {SECRET_FILE_PATH!r}"
    )


def test_ddns_config_forward_ddns_present(host: Host) -> None:
    """forward-ddns must contain at least one domain."""
    ddns = get_dhcpddns(host)
    assert "forward-ddns" in ddns
    domains: JsonList = ddns["forward-ddns"].get("ddns-domains", [])
    assert len(domains) > 0, "forward-ddns ddns-domains must not be empty"


def test_ddns_config_reverse_ddns_present(host: Host) -> None:
    """reverse-ddns must contain at least one domain."""
    ddns = get_dhcpddns(host)
    assert "reverse-ddns" in ddns
    domains: JsonList = ddns["reverse-ddns"].get("ddns-domains", [])
    assert len(domains) > 0, "reverse-ddns ddns-domains must not be empty"


def test_ddns_config_forward_domain_key_name(host: Host) -> None:
    """Each forward DDNS domain must reference a key that exists in tsig-keys."""
    ddns = get_dhcpddns(host)
    tsig_names: set[str] = {k["name"] for k in ddns.get("tsig-keys", [])}
    for domain in ddns["forward-ddns"].get("ddns-domains", []):
        key_name: str = domain.get("key-name", "")
        assert key_name in tsig_names, (
            f"Forward domain {domain.get('name')!r} references key "
            f"{key_name!r} which is not in tsig-keys {tsig_names!r}"
        )


def test_ddns_config_reverse_domain_key_name(host: Host) -> None:
    """Each reverse DDNS domain must reference a key that exists in tsig-keys."""
    ddns = get_dhcpddns(host)
    tsig_names: set[str] = {k["name"] for k in ddns.get("tsig-keys", [])}
    for domain in ddns["reverse-ddns"].get("ddns-domains", []):
        key_name: str = domain.get("key-name", "")
        assert key_name in tsig_names, (
            f"Reverse domain {domain.get('name')!r} references key "
            f"{key_name!r} which is not in tsig-keys {tsig_names!r}"
        )


# ---------------------------------------------------------------------------
# LP #2121327 — AppArmor local override for kea-dhcp-ddns log files
# ---------------------------------------------------------------------------


def test_apparmor_override_file_exists(host: Host) -> None:
    """The LP #2121327 AppArmor local override file must be present.

    deploy_ddns.yml writes a local override to grant kea-dhcp-ddns the
    log-file and log-lock permissions missing from the Ubuntu 3.0.3-1
    package-shipped profile.
    """
    assert host.file(APPARMOR_OVERRIDE_PATH).exists, (
        f"AppArmor override {APPARMOR_OVERRIDE_PATH} is missing — "
        "LP #2121327 workaround was not applied"
    )


def test_apparmor_override_grants_log_rw(host: Host) -> None:
    """Override must grant rw on the kea-dhcp-ddns log file."""
    content: str = host.file(APPARMOR_OVERRIDE_PATH).content_string
    assert "/var/log/kea/kea-dhcp-ddns.log rw," in content, (
        "AppArmor override is missing 'rw' grant for kea-dhcp-ddns.log"
    )


def test_apparmor_override_grants_lock_rwk(host: Host) -> None:
    """Override must grant rwk on the kea-dhcp-ddns log lock file."""
    content: str = host.file(APPARMOR_OVERRIDE_PATH).content_string
    assert "/var/log/kea/kea-dhcp-ddns.log.lock rwk," in content, (
        "AppArmor override is missing 'rwk' grant for kea-dhcp-ddns.log.lock"
    )


# ---------------------------------------------------------------------------
# Systemd service — kea-dhcp-ddns-server
# ---------------------------------------------------------------------------


def test_kea_ddns_service_enabled(host: Host) -> None:
    assert host.service("kea-dhcp-ddns-server").is_enabled


def test_kea_ddns_service_running(host: Host) -> None:
    assert host.service("kea-dhcp-ddns-server").is_running
