# ansible-role-kea-dhcp

[![CI](https://github.com/basictheprogram/ansible-role-kea-dhcp/actions/workflows/ci.yml/badge.svg)](https://github.com/basictheprogram/ansible-role-kea-dhcp/actions/workflows/ci.yml)
[![Ansible Lint](https://github.com/basictheprogram/ansible-role-kea-dhcp/actions/workflows/ansible-lint.yml/badge.svg)](https://github.com/basictheprogram/ansible-role-kea-dhcp/actions/workflows/ansible-lint.yml)
[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-kea__dhcp-blue.svg?style=popout-square)](https://galaxy.ansible.com/realtime/kea_dhcp)
[![Ansible Role](https://img.shields.io/ansible/role/d/realtime/kea_dhcp.svg?style=popout-square)](https://galaxy.ansible.com/realtime/kea_dhcp)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)

An Ansible role that installs and configures [ISC Kea v3][kea-docs] DHCP
natively via `apt` packages on **Ubuntu Resolute (26.04 LTS)**. No Docker
required.

The role supports up to four Kea services:

- `kea-dhcp4` — IPv4 DHCP server
- `kea-dhcp6` — IPv6 DHCP server
- `kea-ctrl-agent` — RESTful control agent
- `kea-dhcp-ddns` — Dynamic DNS update daemon



## Requirements

- Ubuntu Resolute (26.04 LTS)
- Ansible Core 2.20 or later
- ISC Kea v3 available in the Ubuntu apt repositories



## Installation

Move into your `roles/` directory and clone:

```bash
git clone <your-repo-url> ansible-role-kea-dhcp
```

Then include the role in your playbook:

```yaml
- hosts: dhcp_servers
  name: Install Kea DHCP service
  roles:
    - ansible-role-kea-dhcp
```



## Usage

All available variables are defined in [`defaults/main.yml`](./defaults/main.yml).
The most common ones are described below.

### Enabling services

By default only the IPv4 service is enabled:

```yaml
kea_dhcp4_enabled: true
kea_dhcp6_enabled: false
kea_ctrl_agent_enabled: false
kea_ddns_enabled: false
```

### Base directory

All configuration files, leases, logs, and sockets are written under a single
base directory:

```yaml
kea_base_dir: "/etc/kea"
```

### Interfaces

It is strongly recommended to name the interface explicitly rather than using
the wildcard:

```yaml
kea_dhcp_interfaces: [ "eth0" ]
kea_dhcp4_interfaces: "{{ kea_dhcp_interfaces }}"
kea_dhcp6_interfaces: "{{ kea_dhcp_interfaces }}"
```

### Subnets

Subnets are expressed as a list and piped through the `to_nice_json` filter,
giving you the full expressive power of the Kea JSON schema:

```yaml
kea_dhcp4_subnets:
  - id: 1
    subnet: "192.168.1.0/24"
    pools:
      - pool: "192.168.1.100 - 192.168.1.200"
    reservations:
      - hw-address: "aa:bb:cc:dd:ee:ff"
        ip-address: "192.168.1.10"
```

Reservations can also be split into external files under
`kea_reservations_dir` (default `/etc/kea/reservations`) — see
[External reservation files](#external-reservation-files) below.

### Control Agent

```yaml
kea_ctrl_agent_host: "0.0.0.0"
kea_ctrl_agent_port: 8000
```

### Logging

```yaml
# NOTE: !unsafe required to prevent Ansible interpreting {%
kea_logging_pattern: !unsafe "%D{%Y-%m-%d %H:%M:%S.%q} %-5p [%c/%i.%t] %m\n"
kea_logging_severity: "INFO"
kea_logging_debuglevel: 0
kea_logging_maxsize: 10485760  # 10 MB
kea_logging_maxver: 3
```

### Raw / advanced options

For anything not covered by a dedicated variable, pass a dict directly to the
template via the `raw_options` variables:

```yaml
kea_dhcp4_raw_options:
  authoritative: true
  option-def:
    - name: "vendor-encapsulated-options"
      code: 43
      type: "binary"
```

Refer to the [Kea ARM][kea-docs] and the [all-keys example][kea-allkeys] for
the full range of available settings.



## Variables Reference

All variables are defined in [`defaults/main.yml`](./defaults/main.yml) and may
be overridden in `host_vars`, `group_vars`, or at playbook scope. Variables
marked **required** have no meaningful default and must be set for the role to
produce a working configuration.

### Service flags

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp4_enabled` | `true` | Install and start `kea-dhcp4` |
| `kea_dhcp6_enabled` | `false` | Install and start `kea-dhcp6` |
| `kea_ctrl_agent_enabled` | `false` | Install and start `kea-ctrl-agent` |
| `kea_ddns_enabled` | `false` | Install and start `kea-dhcp-ddns` |

### Directory layout

| Variable | Default | Description |
|---|---|---|
| `kea_base_dir` | `/etc/kea` | Kea configuration files |
| `kea_lease_dir` | `/var/lib/kea` | Persistent lease files (created by `kea-common`) |
| `kea_log_dir` | `/var/log/kea` | Kea log files |

These directories are created by the `kea-common` package. The role creates
`{{ kea_base_dir }}/sockets` and ensures `{{ kea_log_dir }}` exists.

### Interfaces

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp_interfaces` | `["*"]` | Interface list shared by `kea-dhcp4` and `kea-dhcp6` |
| `kea_dhcp4_interfaces` | `{{ kea_dhcp_interfaces }}` | Interfaces for `kea-dhcp4` |
| `kea_dhcp6_interfaces` | `{{ kea_dhcp_interfaces }}` | Interfaces for `kea-dhcp6` |

**Required in production.** Always set `kea_dhcp_interfaces` explicitly
(e.g., `["eth0"]`) rather than relying on the `"*"` wildcard. Listening on
all interfaces on a production host is rarely correct.

### Multi-threading

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp_multi_threading_enable` | `true` | Enable multi-threading for all DHCP services |
| `kea_dhcp4_multi_threading_enable` | `{{ kea_dhcp_multi_threading_enable }}` | Override for `kea-dhcp4` |
| `kea_dhcp6_multi_threading_enable` | `{{ kea_dhcp_multi_threading_enable }}` | Override for `kea-dhcp6` |
| `kea_dhcp4_multi_threading_pool_size` | `min(vcpus, 8)` | Thread pool size for `kea-dhcp4` |
| `kea_dhcp6_multi_threading_pool_size` | `min(vcpus, 6)` | Thread pool size for `kea-dhcp6` |
| `kea_dhcp4_multi_threading_queue_size` | `pool_size × 7` | Packet queue size for `kea-dhcp4` |
| `kea_dhcp6_multi_threading_queue_size` | `pool_size × 150` | Packet queue size for `kea-dhcp6` |

Pool sizes are derived from `ansible_facts['processor_vcpus']` at run time.

### Lease timers

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp_valid_lifetime` | `6000` | Shared valid lifetime (seconds) |
| `kea_dhcp4_valid_lifetime` | `{{ kea_dhcp_valid_lifetime }}` | Override for `kea-dhcp4` |
| `kea_dhcp6_valid_lifetime` | `{{ kea_dhcp_valid_lifetime }}` | Override for `kea-dhcp6` |
| `kea_dhcp_renew_timer` | `valid_lifetime × 0.5` | Shared T1 (seconds) |
| `kea_dhcp4_renew_timer` | `{{ kea_dhcp_renew_timer }}` | Override for `kea-dhcp4` |
| `kea_dhcp6_renew_timer` | `{{ kea_dhcp_renew_timer }}` | Override for `kea-dhcp6` |
| `kea_dhcp_rebind_timer` | `valid_lifetime × 0.85` | Shared T2 (seconds) |
| `kea_dhcp4_rebind_timer` | `{{ kea_dhcp_rebind_timer }}` | Override for `kea-dhcp4` |
| `kea_dhcp6_rebind_timer` | `{{ kea_dhcp_rebind_timer }}` | Override for `kea-dhcp6` |
| `kea_dhcp_parked_packet_limit` | `128` | Shared parked-packet limit |
| `kea_dhcp4_parked_packet_limit` | `{{ kea_dhcp_parked_packet_limit }}` | Override for `kea-dhcp4` |
| `kea_dhcp6_parked_packet_limit` | `{{ kea_dhcp_parked_packet_limit }}` | Override for `kea-dhcp6` |

### Subnets

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp4_subnets` | `[]` | DHCPv4 subnet list — **required** when `kea_dhcp4_enabled: true` |
| `kea_dhcp6_subnets` | `[]` | DHCPv6 subnet list — **required** when `kea_dhcp6_enabled: true` |
| `kea_reservations_dir` | `/etc/kea/reservations` | Directory scanned for a subnet's `reservation_files` |

Each list entry maps directly to a Kea `subnet4` or `subnet6` object. The
`id` field must be unique and stable. Example:

```yaml
kea_dhcp4_subnets:
  - id: 1
    subnet: "192.168.1.0/24"
    pools:
      - pool: "192.168.1.100 - 192.168.1.200"
    reservations:
      - hw-address: "aa:bb:cc:dd:ee:ff"
        ip-address: "192.168.1.10"
    option-data:
      - name: "routers"
        data: "192.168.1.1"
```

See the [Kea all-keys example][kea-allkeys] for the full range of subnet
options.

### External reservation files

| Variable | Default | Description |
|---|---|---|
| `kea_reservations_dir` | `/etc/kea/reservations` | Directory scanned for a subnet's `reservation_files` |

Each `kea_dhcp4_subnets` entry may optionally list `reservation_files` —
bare filenames (no `/`) resolved under `kea_reservations_dir`. Each file
must be a standalone JSON array of reservation objects, for example one
deployed by a separate role like
[`ansible-role-netbox_printer_reservations`](../ansible-role-netbox_printer_reservations).
Entries from every listed file are appended to that subnet's inline
`reservations:` list and fully inlined into `kea-dhcp4.conf` — this role
does not use Kea's `<?include?>` directive, so the rendered config always
stays a single, standard JSON document.

```yaml
kea_dhcp4_subnets:
  - id: 1
    subnet: "192.168.1.0/24"
    pools:
      - pool: "192.168.1.100 - 192.168.1.200"
    reservation_files:
      - printers.json
```

A listed file that does not yet exist on disk is created as an empty `[]`
placeholder rather than failing the run — useful the first time this role
runs before a writer role like `ansible-role-netbox_printer_reservations`
has ever deployed anything. Because the file is read at the moment this
role's tasks execute, the writer role must run earlier in the same
playbook for its updates to reach the live config — see that role's own
`kea-dhcp4` reload handler, which does not by itself cause this role to
re-render `kea-dhcp4.conf`.

### Control Agent

| Variable | Default | Description |
|---|---|---|
| `kea_ctrl_agent_host` | `"0.0.0.0"` | HTTP bind address for `kea-ctrl-agent` |
| `kea_ctrl_agent_port` | `8000` | HTTP bind port for `kea-ctrl-agent` |
| `kea_ctrl_agent_raw_options` | `{}` | Pass-through dict for additional ctrl-agent settings |

### DDNS

| Variable | Default | Description |
|---|---|---|
| `kea_ddns_host` | `"127.0.0.1"` | Address `kea-dhcp-ddns` listens on (also used by dhcp4/dhcp6 to reach it) |
| `kea_ddns_port` | `53001` | Port `kea-dhcp-ddns` listens on |
| `kea_tsig_keys` | `[]` | TSIG key list — **required** when `kea_ddns_enabled: true` |
| `kea_forward_ddns` | `[]` | Forward DDNS zone list — **required** when `kea_ddns_enabled: true` |
| `kea_reverse_ddns` | `[]` | Reverse DDNS zone list — **required** when `kea_ddns_enabled: true` |

Each `kea_tsig_keys` entry:

```yaml
kea_tsig_keys:
  - name: "d2.sha512.key"
    algorithm: "HMAC-SHA512"
    secret-file: "/etc/kea/d2.sha512.key"
```

Each `kea_forward_ddns` / `kea_reverse_ddns` entry:

```yaml
kea_forward_ddns:
  - comment: "Forward zone for example.com"
    name: "example.com."
    key-name: "d2.sha512.key"
    dns_servers:
      - ip-address: "192.168.1.53"
        port: 53
```

`key-name` is required on every `kea_forward_ddns` / `kea_reverse_ddns`
entry and must match the `name` of an entry in the final `kea_tsig_keys`
list. That list can come from `kea_tsig_keys` entries defined directly in
`host_vars`, from keys auto-discovered on the BIND9 host at
`kea_bind9_keys_path` (see `tasks/key_management.yml`), or both — either
way, the final merged list isn't known until `key_management.yml` has run.
Before rendering
`kea-dhcp-ddns.conf`, `deploy_ddns.yml` asserts this for every zone and
fails with a clear message naming the zone, the missing key, and the known
key names if it doesn't hold. The rendered config is then checked with
`kea-dhcp-ddns -t` — the same validation `deploy_dhcp.yml` already runs for
`kea-dhcp4`/`kea-dhcp6` — before the service is (re)started, so a broken
DDNS config fails the Ansible run instead of `kea-dhcp-ddns-server` failing
to start on the host.

### Logging

| Variable | Default | Description |
|---|---|---|
| `kea_logging_severity` | `"INFO"` | Log level (`DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL`) |
| `kea_logging_debuglevel` | `0` | Debug verbosity (0–99, only relevant when severity is `DEBUG`) |
| `kea_logging_maxsize` | `10485760` | Maximum log file size in bytes (10 MB) |
| `kea_logging_maxver` | `3` | Number of rotated log files to keep |
| `kea_logging_pattern` | see defaults | Log line format string (`!unsafe` required in YAML) |
| `kea_logging_raw_dhcp4` | see defaults | Full logger config list for `kea-dhcp4` |
| `kea_logging_raw_dhcp6` | see defaults | Full logger config list for `kea-dhcp6` |
| `kea_logging_raw_ctrl_agent` | see defaults | Full logger config list for `kea-ctrl-agent` |
| `kea_logging_raw_ddns` | see defaults | Full logger config list for `kea-dhcp-ddns` |

The `kea_logging_raw_*` variables render directly into the `"loggers"` key of
each service's JSON config. Override them entirely if you need multiple
appenders or per-logger severity overrides.

### Raw / pass-through options

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp4_raw_options` | `{}` | Extra top-level keys injected into `kea-dhcp4.conf` |
| `kea_dhcp6_raw_options` | `{}` | Extra top-level keys injected into `kea-dhcp6.conf` |
| `kea_ctrl_agent_raw_options` | `{}` | Extra top-level keys injected into `kea-ctrl-agent.conf` |

Keys and values are serialized with `to_nice_json` and written verbatim into
the rendered configuration. Use these for any Kea setting not covered by a
dedicated variable.




## Known issues

### LP #2121327 — `kea-dhcp-ddns` AppArmor log lock denial (isc-kea 3.0.3-1)

The Ubuntu 3.0.3-1 package ships an AppArmor profile for `kea-dhcp-ddns` that
is missing permissions for both the log file and its lock file, producing audit
denials in `dmesg`:

```
apparmor="DENIED" operation="mknod" profile="kea-dhcp-ddns"
  name="/var/log/kea/kea-dhcp-ddns.log" ...
apparmor="DENIED" operation="mknod" profile="kea-dhcp-ddns"
  name="/var/log/kea/kea-dhcp-ddns.log.lock" ...
```

This role works around the package bug by writing a local AppArmor override to
`/etc/apparmor.d/local/usr.sbin.kea-dhcp-ddns` and reloading the profile.
The override (and the reload) is skipped entirely on hosts without
`apparmor_parser` (`/usr/sbin/apparmor_parser`) installed, since there is no
AppArmor profile to override in that case.
The override file survives package upgrades and will be left in place until
explicitly removed. Once ISC or Ubuntu ships a corrected `isc-kea` package the
override file can be deleted and the AppArmor profile reloaded — the role does
not remove it automatically.

Monitor [Ubuntu bug LP #2121327](https://bugs.launchpad.net/ubuntu/+source/isc-kea/+bug/2121327)
for a package-level fix.



## Upstream projects

This role would not exist without the work of:

- **Jonas Alfredsson** — [ansible-role-kea_dhcp][upstream-jonas]
  The original Ansible role for Kea DHCP using Docker containers, including
  the Jinja2 configuration templates that underpin this project.

This project is the second fork by the same author. The intermediate
Docker-based fork ([ansible-role-kea-dhcp-docker][upstream-basic]) is also
maintained by Bob Tanner under the GitHub handle `basictheprogram`.

See the [NOTICE](./NOTICE) file for full attribution details.



## License

GNU General Public License v3.0 or later — see [LICENSE](./LICENSE).

## Author

Copyright (C) 2026  Bob Tanner



[kea-docs]: https://kea.readthedocs.io/en/latest/arm/intro.html
[kea-allkeys]: https://github.com/isc-projects/kea/blob/master/doc/examples/kea4/all-keys.json
[upstream-jonas]: https://github.com/JonasAlfredsson/ansible-role-kea_dhcp
[upstream-basic]: https://github.com/basictheprogram/ansible-role-kea-dhcp-docker
