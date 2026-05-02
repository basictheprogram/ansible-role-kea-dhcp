# ansible-role-kea-dhcp

An Ansible role that installs and configures [ISC Kea v3][kea-docs] DHCP
natively via `apt` packages on **Ubuntu Resolute (26.04 LTS)**. No Docker
required.

The role supports up to three Kea services:

- `kea-dhcp4` — IPv4 DHCP server
- `kea-dhcp6` — IPv6 DHCP server
- `kea-ctrl-agent` — RESTful control agent
- `kea-dhcp-ddns` — Dynamic DNS update daemon



## Requirements

- Ubuntu Resolute (26.04 LTS)
- Ansible Core 2.17 or later
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

Copyright (C) 2026  Bob Tanner \<tanner@real-time.com\>



[kea-docs]: https://kea.readthedocs.io/en/latest/arm/intro.html
[kea-allkeys]: https://github.com/isc-projects/kea/blob/master/doc/examples/kea4/all-keys.json
[upstream-jonas]: https://github.com/JonasAlfredsson/ansible-role-kea_dhcp
[upstream-basic]: https://github.com/basictheprogram/ansible-role-kea-dhcp-docker
