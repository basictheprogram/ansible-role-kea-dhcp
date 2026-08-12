# Project Context — ansible-role-kea-dhcp

This file is the project brief for Claude. Upload it as project knowledge
when creating this project in Claude (claude.ai → Projects → New Project →
Add Knowledge).

---

## What This Project Is

An Ansible role that installs and configures [ISC Kea v3][kea-docs] DHCP
natively via `apt` packages on **Ubuntu Resolute (26.04 LTS)**. No Docker.
No extra collections beyond `ansible.builtin`. The role manages up to four
Kea services — `kea-dhcp4`, `kea-dhcp6`, `kea-ctrl-agent`, and
`kea-dhcp-ddns` — driven entirely by variables in `defaults/main.yml`.

This role is a fork of [ansible-role-kea-dhcp-docker][upstream-basic]
(also by Bob Tanner / basictheprogram), which was itself forked from
[ansible-role-kea_dhcp][upstream-jonas] by Jonas Alfredsson. Neither
upstream will receive PRs from this project. See NOTICE for attribution.

---

## Scope Constraints

These boundaries are hard. Do not relax them without an explicit decision from
the human, and always flag the request before proceeding.

* **Ubuntu Resolute (26.04 LTS) only.** No other Ubuntu releases, no Debian,
  no RHEL, no Alpine. `tasks/pre-flight.yml` asserts
  `ansible_facts['distribution'] == "Ubuntu"` and
  `ansible_facts['distribution_version'] == "26.04"` at runtime, and
  `meta/main.yml`'s `description:` states the supported platform for Galaxy
  browsing. (There is no `galaxy_info.platforms:` key — Galaxy ignores that
  field and ansible-lint's schema validator for it has a long-standing
  false-positive bug.) If asked to add another distro, decline and explain
  why this role exists specifically for Resolute's Kea v3 apt packages.

* **ISC Kea v3 only.** The role installs the `kea-dhcp4-server`,
  `kea-dhcp6-server`, `kea-ctrl-agent`, and `kea-dhcp-ddns-server` apt
  packages shipped in Ubuntu Resolute's repositories (Kea v3). In Ubuntu
  Resolute the systemd unit names match the package names: `kea-dhcp4-server`,
  `kea-dhcp6-server`, `kea-dhcp-ddns-server`, and `kea-ctrl-agent`. Do not
  add workarounds for Kea v2 behaviour or speculative support for a future
  Kea v4.

* **`ansible.builtin` only — no external collections.** Everything the role
  needs (`apt`, `template`, `systemd`, `file`, `copy`, `find`, `slurp`) is
  in `ansible.builtin`. Do not introduce `community.general`,
  `ansible.posix`, `community.docker`, or any other collection dependency.

* **No Docker, no containers.** See "Settled Decisions" below.

---

## Source of Truth

This `CLAUDE.md` is the authoritative spec for the role. Read it before
making any non-trivial change. Variable names, schemas, file layout, key
design decisions, and commit conventions live here.

If something in the code disagrees with this file, this file is right
unless explicitly told otherwise — flag the discrepancy and ask before
"fixing" the design to match the code.

---

## Behavioral Guidelines

Adapted from the [Karpathy CLAUDE.md][karpathy-claude] behavioral guidelines.
These bias toward caution over speed. For trivial tasks, use judgment.

Note: The article at https://levelup.gitconnected.com/the-4-lines-every-claude-md-needs-2717a46866f6
was referenced as a source for this section but is behind a paywall and could
not be retrieved. The Karpathy guidelines below cover the same ground.

### 1. Think Before Changing

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing any task:

* State assumptions about target system state explicitly. If uncertain, ask.
* If multiple interpretations exist, present them — don't pick silently.
  For example: "This could mean adding a variable to `defaults/` or
  hard-coding it in the template — which do you want?"
* If a simpler approach exists, say so. Push back when warranted.
* If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum change that solves the problem. Nothing speculative.**

* No new variables in `defaults/main.yml` beyond what the task requires.
  Every new variable is a public interface change for consumers.
* No new Jinja2 abstractions for single-use template blocks.
* No "flexibility" or "future-proofing" that wasn't requested.
* No error handling for scenarios the role cannot encounter on Ubuntu
  Resolute with Kea v3 apt packages.
* If you write 50 lines of tasks and it could be 20, rewrite it.

Ask yourself: "Would a senior Ansible engineer say this is overcomplicated?"
If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing tasks, templates, handlers, or defaults:

* Don't "improve" adjacent tasks, comments, or formatting.
* Don't refactor things that aren't broken.
* Match existing YAML style, even if you'd do it differently.
* If you notice an unrelated issue (unused variable, wrong mode, stale
  comment), mention it — don't silently fix it.

When your changes create orphans:

* Remove variables, handler notify strings, or task references that YOUR
  changes made unused.
* Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals before starting:

* "Add DHCPv6 support" → "molecule converge passes with
  `kea_dhcp6_enabled: true`; second run reports zero changes"
* "Fix handler wiring" → "handler name matches every `notify:` string
  that references it; pre-commit lint passes"
* "Update defaults" → "pre-commit lint passes; no consumer variable
  renamed or removed without a BREAKING CHANGE footer"

For multi-step tasks, state a brief plan before touching any file:

```
1. [step] → verify: [check]
2. [step] → verify: [check]
3. [step] → verify: [check]
```

Strong success criteria allow independent looping. Weak criteria
("make it work") require constant clarification.

---

## Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| Package source | Ubuntu apt repos | Kea v3 available in Ubuntu Resolute (26.04 LTS) |
| Service manager | systemd | `ansible.builtin.systemd` for start/enable/reload |
| Config format | Kea JSON via Jinja2 | All config rendered from `templates/*.json.j2` |
| TSIG keys | `key_management.yml` | Generated on control node, pushed to managed host |
| Ansible minimum | 2.20 | Matches `meta/main.yml` and the realtime org standard |
| Namespace | `realtime` | Ansible Galaxy namespace for Real Time Enterprises, Inc. |

---

## Role File Structure

```
ansible-role-kea-dhcp/
  tasks/
    main.yml             # Orchestrates service deployments
    deploy_dhcp.yml      # DHCPv4 and DHCPv6 install, config, and service tasks
    deploy_ddns.yml      # DDNS install, config, and service tasks
    key_management.yml   # TSIG key generation and distribution
    merge_reservations.yml  # Merges external reservation files into DHCPv4 subnets
  defaults/main.yml      # All role variables with defaults — public interface
  handlers/main.yml      # Service reload and restart handlers
  templates/
    dhcp4.json.j2        # kea-dhcp4 configuration
    dhcp6.json.j2        # kea-dhcp6 configuration
    ctrl-agent.json.j2   # kea-ctrl-agent configuration
    ddns.json.j2         # kea-dhcp-ddns configuration
  meta/main.yml          # Galaxy metadata (Resolute support noted in description)
  molecule/
    default/
      molecule.yml       # Docker driver, image driven by env vars
      converge.yml       # Framework placeholder (role include pending)
      verify.yml         # Always-pass assertion
  .github/
    workflows/
      ansible-lint.yml   # Lint CI on push/PR to main or master
      molecule.yml       # Molecule CI with distro matrix strategy
  README.md
  NOTICE                 # Upstream attribution
  LICENSE                # GPL-3.0-or-later
  CLAUDE.md              # This file
```

---

## Conventions

* **Commits**: follow the "Git commit message constraints" section below
  exactly. Conventional Commits, imperative mood, body wrapped at 72
  characters, asterisk bullets.
* **Lint**: `.ansible-lint`, `.yamllint`, and `.pre-commit-config.yaml`
  define the rules. Run `pre-commit run --all-files` before every commit.
* **Molecule**: run `molecule test` locally before pushing. The CI matrix
  runs on Ubuntu Resolute (`ubuntu:26.04`).
* **Secrets**: never write TSIG key material or passwords into tracked
  files. Use `no_log: true` on any task that handles key material.
* **Modules**: use FQCNs throughout (`ansible.builtin.apt`,
  `ansible.builtin.template`, `ansible.builtin.systemd`, etc.).
* **Idempotency**: every task must be safe to re-run. Template tasks are
  idempotent by design. Service tasks must not restart unless config
  actually changed — use handlers, not `state: restarted`.
* **Site-specific values**: subnet definitions, interface names, TSIG keys,
  and hostnames must never be hard-coded in the role. They belong in
  `host_vars`, `group_vars`, or inventory.

---

## Settled Decisions — Don't Re-Litigate

These are locked. Don't propose alternatives unless the human raises them:

* **Native packages only — no Docker.** The role uses
  `ansible.builtin.apt` to install Kea from Ubuntu's apt repositories.
  There is no container runtime dependency. Don't add `community.docker`
  tasks.

* **All Kea configuration is template-driven.** Every `*.json.j2` in
  `templates/` is the single source of truth for that service's config.
  Never manage Kea config files with `ansible.builtin.copy` or inline
  `content:` — always go through the template.

* **Handlers, not immediate restarts.** Config changes notify handlers
  (`Reload kea-dhcp4-server`, etc.). Tasks must never use `state: restarted`
  directly. The handlers themselves use `state: restarted` because the
  `kea-dhcp*-server.service` units do not define `ExecReload`; this is still
  correct because handlers only fire when config actually changed.

* **TSIG keys are generated on the control node and pushed.** The
  `key_management.yml` task file owns all key lifecycle. Never generate
  keys on the managed host.

* **`no_log` on all TSIG key tasks.** Any task that touches raw key
  material must set `no_log: true`. This is not optional.

* **One variable file — `defaults/main.yml`.** There is no `vars/main.yml`
  in this role. All variables live in `defaults/` so consumers can override
  every one of them. Don't introduce a `vars/main.yml`.

---

## Key Modules

### `ansible.builtin.apt`
Installs Kea packages. Key params:
- `name` — list of kea package names
- `state: present`
- `update_cache: true` on first run
- Idempotent — safe to re-run.

### `ansible.builtin.template`
Renders Jinja2 templates to Kea JSON config files. Key params:
- `src` — `*.json.j2` from `templates/`
- `dest` — path under `kea_base_dir/`
- `owner`, `group`, `mode`
- Notifies the appropriate reload handler.

### `ansible.builtin.systemd`
Manages Kea services. Key params:
- `name` — e.g., `kea-dhcp4`
- `state: started`, `enabled: true`
- Used in handlers for `state: reloaded`.

### `ansible.builtin.file`
Creates base directories with correct ownership and permissions.

---

## Variables Reference

All variables are defined in `defaults/main.yml` — that file is the
canonical reference. The most consumer-visible ones are:

| Variable | Default | Description |
|---|---|---|
| `kea_dhcp4_enabled` | `true` | Install and start kea-dhcp4 |
| `kea_dhcp6_enabled` | `false` | Install and start kea-dhcp6 |
| `kea_ctrl_agent_enabled` | `false` | Install and start kea-ctrl-agent |
| `kea_ddns_enabled` | `false` | Install and start kea-dhcp-ddns |
| `kea_base_dir` | `"/etc/kea"` | Base directory for all Kea config files |
| `kea_dhcp_interfaces` | `[ "*" ]` | Interface list shared by dhcp4 and dhcp6 |
| `kea_dhcp4_subnets` | `[]` | DHCPv4 subnet list — see format below |
| `kea_dhcp6_subnets` | `[]` | DHCPv6 subnet list |
| `kea_ctrl_agent_host` | `"0.0.0.0"` | Control agent bind address |
| `kea_ctrl_agent_port` | `8000` | Control agent bind port |
| `kea_logging_severity` | `"INFO"` | Log level for all services |
| `kea_reservations_dir` | `"/etc/kea/reservations"` | Directory scanned for a subnet's `reservation_files` |

### `kea_dhcp4_subnets` entry format

```yaml
kea_dhcp4_subnets:
  - id: 1
    subnet: "192.168.1.0/24"
    pools:
      - pool: "192.168.1.100 - 192.168.1.200"
    reservations:
      - hw-address: "aa:bb:cc:dd:ee:ff"
        ip-address: "192.168.1.10"
    # Optional — filenames (bare, no '/') resolved under kea_reservations_dir.
    # Each file must be a standalone JSON array of reservation objects
    # (e.g. deployed by ansible-role-netbox_printer_reservations). Entries
    # are appended to reservations: above and fully inlined into
    # kea-dhcp4.conf by merge_reservations.yml — no Kea <?include?>
    # directive is used. A missing file is created as an empty placeholder
    # (`[]`) rather than failing the run.
    reservation_files:
      - printers.json
    option-data:
      - name: "routers"
        data: "192.168.1.1"
```

Refer to the [Kea all-keys example][kea-allkeys] for the full range of
available subnet options.

---

## First-Time Setup

1. **Install the role** into your playbooks repo's `roles/` directory.

2. **Define your subnets** — set `kea_dhcp4_subnets` (and `kea_dhcp6_subnets`
   if needed) in `host_vars` or `group_vars`.

3. **Enable the services you need** — flip `kea_dhcp6_enabled`,
   `kea_ctrl_agent_enabled`, or `kea_ddns_enabled` to `true` as required.

4. **Run the playbook:**
   ```bash
   ansible-playbook playbook.yml -i inventory/hosts.yml
   ```

5. **Verify idempotency** — re-run immediately. The second run must report
   zero changes.

---

## Testing Locally

```bash
# Lint pass — run before every commit
pre-commit run --all-files

# Full molecule run against ubuntu:26.04
molecule test

# Faster iteration — skip destroy/create
molecule converge
molecule verify
```

---

## Known Gotchas

* **`ubuntu:26.04` in Molecule does not run systemd by default.** The
  current molecule scenario uses a minimal container for framework testing
  only. When verify tasks need to assert service state, the platform
  definition will need a systemd-capable image and `command: /sbin/init`.
* **Kea config is strict JSON** — trailing commas or invalid syntax cause
  `kea-dhcp4` to fail on reload. Always validate templates with
  `kea-dhcp4 -t /etc/kea/kea-dhcp4.conf` after changes.
* **File mode `"0640"` on config files** — Kea drops privileges and reads
  config as the `_kea` user. Ensure `group: _kea` and `mode: "0640"` on
  all config files.
* **Subnet ID uniqueness** — `id:` values in `kea_dhcp4_subnets` must be
  unique and stable. Changing an ID is not idempotent from Kea's
  perspective.
* **`reservation_files` requires the writer role to run first.**
  `merge_reservations.yml` slurps each listed file's *current* content on
  this host at the moment this role's tasks run. If
  `ansible-role-netbox_printer_reservations` (or any other writer) updates
  a file *after* this role last rendered `kea-dhcp4.conf`, those changes
  will not appear in the live config until this role's tasks run again.
  Both roles must run in the same playbook, writer role first, for
  reservation updates to actually take effect. A file listed in
  `reservation_files` that does not yet exist on disk is created as an
  empty `[]` placeholder rather than failing pre-flight — this keeps a
  first-ever bootstrap run (before the writer role has ever deployed
  anything) from failing.
* **Kea's `<?include?>` directive is intentionally not used.** The
  docker-era templates used `<?include "/kea/config/subnet4.json"?>`.
  The native-apt templates (including `merge_reservations.yml`'s handling
  of `reservation_files`) always fully inline content instead, so
  `kea-dhcp4.conf` stays a single, standard JSON document parseable by
  plain `json.load` — see
  `molecule/default/tests/test_default.py::test_config_file_no_include_directives`.
  This also avoids the `<?include?>` incompatibility with `config-write`-based
  tooling (Stork, the `subnet_cmds` hook, or a manual `config-write` over
  the control socket) documented in ISC's own Kea config-includes guide.
* **AppArmor profiles hardcode control socket names.** The Ubuntu 3.0.3
  package ships AppArmor profiles that allow only specific socket names in
  `/run/kea/`. The role uses the exact names the profiles expect:
  `kea4-ctrl-socket`, `kea6-ctrl-socket`, and `kea-ddns-ctrl-socket`.
  Do not rename these. Any change will result in AppArmor denying the
  `.lock` file creation and the service will fail to start.
* **`kea-dhcp-ddns` log file permissions — Ubuntu LP: #2121327.** The shipped
  AppArmor profile for `kea-dhcp-ddns` in Ubuntu 3.0.3-1 is missing `rw`
  for `/var/log/kea/kea-dhcp-ddns.log` and `rwk` for its `.lock` file. The
  role works around this by writing a local override to
  `/etc/apparmor.d/local/usr.sbin.kea-dhcp-ddns` and reloading the profile
  via `apparmor_parser -r`. Do not patch the package-owned profile directly.
  Remove the local override file once the upstream package is fixed.

---

## Working With the Consumer Side

This role is consumed from the playbooks repo. Inventory layout,
`group_vars`, and `host_vars` live there, not here. When the human asks
about consumer-side changes, ask which inventory repo to operate on — it
is not in this directory tree.

---

## Git Commit Message Constraints

You are an expert DevOps engineer and professional git commit message
writer. Your task is to generate a high-quality git commit message based
on the currently staged changes in the `ansible-role-kea-dhcp` repository.

### Step 1 — Retrieve Changes

Run:

```
git diff --cached
```

Analyze the full staged diff. This is the **single source of truth** for
what will be committed.

### Step 2 — Understand the Change

Determine:

* The **primary purpose** of the change
* The **type of change** (feature, bug fix, refactor, etc.)
* The **most relevant scope** within the role
* Whether the change introduces a **breaking change** for role consumers
* Whether multiple changes should be summarized together

Pay special attention to:

* Changes to `defaults/main.yml` — these define the role's public interface;
  any renamed or removed variable is a breaking change for consumers
* Changes to `kea_dhcp4_subnets` or `kea_dhcp6_subnets` schema — a new
  optional key is additive, a renamed or removed key breaks every consumer
* Changes to Jinja2 templates — config structure changes may require
  consumers to migrate existing Kea state
* Changes to `meta/main.yml` — galaxy metadata, minimum Ansible version,
  or supported Ubuntu platforms
* Changes to `molecule/` — test coverage and CI matrix
* Changes to handlers — incorrect handler names break the notify chain

If multiple files are modified, identify the **dominant intent** rather
than listing every file.

### Step 3 — Select Commit Type

Use Conventional Commits:

* feat — new task, variable, template feature, or capability
* fix — bug fix, idempotency correction, or handler wiring fix
* docs — README, NOTICE, CLAUDE.md, or inline YAML comments
* style — YAML formatting, whitespace, ansible-lint cleanup
* refactor — restructure tasks or templates without behavior change
* perf — performance improvement (e.g., reduced apt calls, fewer loops)
* test — molecule scenarios, verify tasks, lint config
* chore — galaxy metadata, tooling, pre-commit hook updates
* ci — GitHub Actions workflows, dependabot config

### Step 4 — Determine Scope

Infer a scope from the role layout or the Kea subsystem being changed.

Common role-layout scopes:

* tasks
* defaults
* handlers
* templates
* meta
* molecule

Common Kea / role-feature scopes:

* dhcp4
* dhcp6
* ctrl-agent
* ddns
* keys
* subnets
* interfaces
* logging
* packages

Only include a scope when it adds clarity. Prefer the Kea-feature scope
for feature-driven changes (e.g., `feat(ddns): ...`, `feat(keys): ...`)
and the role-layout scope for structural changes
(e.g., `refactor(tasks): ...`, `chore(meta): ...`).

### Step 5 — Write the Commit Message

Format exactly as:

```
<type>[optional scope]: <short summary (<=50 chars)>

<body wrapped at 72 characters>

[optional footer(s)]
```

#### Subject Line Rules

* Use **imperative mood** ("Add", "Fix", "Update", "Remove")
* Maximum **50 characters**
* Describe the **result**, not the implementation
* Prefer Kea or Ansible terminology over generic phrasing
  (e.g., "Add TSIG key rotation task", not "Add new feature")

#### Body Rules

The body is **required**.

Explain **why the change was made**, focusing on:

* What Kea deployment scenario or ISC behavior motivated it
* What downstream role consumers need to know to upgrade safely
* Any Kea version, Ubuntu Resolute package, or Ansible version constraints

When helpful, summarize key changes using bullet points.

#### Bullet Rules

* Use `*` (asterisk) for all bullets
* Do NOT use `-` or `•`
* Nested bullets must be indented with two spaces
* Do not use Markdown formatting of any kind

Example:

```
* Add kea_dhcp4_raw_options to defaults
* Wire raw options into dhcp4.json.j2 via to_nice_json
  * Preserves all existing behavior when variable is empty dict
```

#### Ansible-Specific Expectations

* Call out new, renamed, or removed default variables — these are part
  of the role's public interface
* Note when handler names change — consumers' playbooks may reference them
* Mention idempotency impact when relevant
* Flag changes to `meta/main.yml` (namespace, min version, platforms)
* Note when molecule test coverage changes

#### Kea-Specific Expectations

* Distinguish between changes to dhcp4, dhcp6, ctrl-agent, and ddns —
  they have separate config files, service units, and task includes
* Note when a template change alters the rendered JSON structure —
  consumers with existing Kea leases or reservations may need to
  verify state after upgrade
* Call out changes to `key_management.yml` and `no_log` usage
* Highlight changes to subnet schema or pool definitions
* Note changes to systemd service dependencies (e.g., ddns must start
  before dhcp4 if DDNS is enabled)
* Flag changes to file ownership or permissions on config files —
  the `_kea` user and `"0640"` mode are load-bearing

---

### Breaking Changes

A change is breaking when it:

* Renames or removes a variable in `defaults/main.yml`
* Changes a default value in a way that alters runtime behavior
  (e.g., flipping `kea_dhcp4_enabled` to `false`)
* Renames or removes a key inside `kea_dhcp4_subnets` or
  `kea_dhcp6_subnets` entries
* Renames a public handler (breaks notify chains in consumer playbooks)
* Changes a Jinja2 template in a way that alters the rendered config
  structure and requires manual Kea state migration
* Drops Ubuntu Resolute support (the `tasks/pre-flight.yml` platform
  assertion or the statement in `meta/main.yml`'s `description:`)
* Bumps the minimum Ansible version in `meta/main.yml`
* Changes file paths under `kea_base_dir` that consumers reference
  directly

If the diff introduces a breaking change:

* Add `!` after the type/scope in the subject
* Include a footer: `BREAKING CHANGE: <description>`

### Examples

```
feat(ddns): add TSIG key rotation task
fix(templates): correct lease-database path for apt install
refactor(tasks): split deploy_dhcp into per-service files
test(molecule): add verify task for kea-dhcp4 service state
ci(molecule): add noble to distro matrix
chore(meta): update Galaxy namespace to realtime
docs(readme): document subnet reservation format

feat(defaults)!: rename kea_container_base_dir to kea_base_dir

BREAKING CHANGE: kea_container_base_dir is now kea_base_dir; update
host_vars and group_vars before upgrading.
```

---

### Output Rules

When asked to generate a commit message, return **ONLY the commit
message**.

Do NOT include:

* explanations
* analysis
* the diff
* markdown formatting
* code fences

The output must be a **clean commit message ready for `git commit`**.
The output will be pasted directly into a git commit editor; optimize
for copy/paste fidelity over styling.

---

## Notes

* `defaults/main.yml` forms the role's public interface — treat every
  change there as consumer-visible.
* All Kea configuration is rendered from `templates/*.json.j2` — never
  manage Kea JSON files with `copy` or inline `content`.
* TSIG key material must never appear in Ansible output — `no_log: true`
  on every task in `key_management.yml`.
* The molecule scenario is currently a framework placeholder. When native-
  package implementation is complete, replace the converge placeholder with
  the actual role include and add service-state assertions to verify.

---

## How to Continue This Work in Claude

When starting a new conversation in this project, Claude will have this
file as project knowledge. You can ask things like:

* "Rewrite tasks/main.yml and tasks/deploy_dhcp.yml for native apt packages"
* "Add a verify task that checks the kea-dhcp4 service is running"
* "Add TSIG key rotation support to key_management.yml"
* "Add Ubuntu Noble to the molecule matrix"
* "Help me write a subnet reservation for a specific MAC address"
* "Generate a commit message for the current staged changes"

---

## When in Doubt

Read this file end-to-end, then ask. The settled decisions above are
load-bearing — they reflect deliberate choices, not defaults.

---

*Last updated by Claude on 2026-05-08*

[kea-docs]: https://kea.readthedocs.io/en/latest/arm/intro.html
[kea-allkeys]: https://github.com/isc-projects/kea/blob/master/doc/examples/kea4/all-keys.json
[upstream-basic]: https://github.com/basictheprogram/ansible-role-kea-dhcp-docker
[upstream-jonas]: https://github.com/JonasAlfredsson/ansible-role-kea_dhcp
[karpathy-claude]: https://github.com/forrestchang/andrej-karpathy-skills/blob/main/CLAUDE.md
