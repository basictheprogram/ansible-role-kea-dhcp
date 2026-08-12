# TODO — ansible-sync-role session (2026-08-12)

Items flagged during this sync but not resolved in this session. Carries
forward unresolved items from the 2026-07-08 session's TODO.md; resolved
items from that session have been dropped (see notes below).

## 1. `.github/workflows/molecule.yml` looks possibly redundant/dead

Carried forward, unchanged, from the 2026-07-08 session — not investigated
this session either. `.github/workflows/ci.yml` already has its own
`molecule` job (runs `molecule test`, no matrix). `.github/workflows/molecule.yml`
is a second, separate workflow that runs `molecule test --all` on push/PR
to main/master, using a `matrix.distro`/`matrix.image` strategy that sets
`MOLECULE_DISTRO`/`MOLECULE_IMAGE` env vars — but neither
`molecule/default/molecule.yml` nor `molecule/ddns/molecule.yml` reads
those env vars (both hardcode `geerlingguy/docker-ubuntu2604-ansible:latest`
directly, correctly, since this role only ever targets one platform). This
means the matrix strategy is currently a no-op. Investigate whether
`molecule.yml` should be removed (duplicate of `ci.yml`'s job) or deleted
outright, now that Steps 9/10 have confirmed the single-platform molecule
scenarios are otherwise fully compliant. Out of scope for this skill
(Procedure B only covers legacy, non-GitHub-Actions CI systems).

## 2. CLAUDE.md's role file structure listing omits `tasks/merge_reservations.yml`

Pre-existing-style gap, same class as the 2026-07-08 session's item #4
(which was about `pre-flight.yml` and has since been fixed in CLAUDE.md).
CLAUDE.md's "Role File Structure" tree already lists `merge_reservations.yml`
correctly (added in the ansible-commit session earlier today), so this is
just a note that the structure section should be spot-checked again next
time a task file is added or removed — not an active gap right now.

## 3. `meta/argument_specs.yml` — still skipped, still not required

Re-confirmed this session (Step 4 audit): no `.ansible-lint` rule currently
enabled requires it, and README's Variables Reference documents all
`defaults/main.yml` keys by hand. Same standing decision as the
2026-07-08 session's item #5. Revisit only if `argument_specs` schema
validation becomes a project requirement.

## 4. CLAUDE.md kept as-is over the generic template (Step 2)

The existing `CLAUDE.md` is a hand-written project brief (Scope
Constraints, Settled Decisions, full Variables Reference, a custom commit
message guide) that's substantially richer than what `_template/CLAUDE.md`
would generate — several of the template's placeholder sections would
have become bare `TODO` stubs since no `DESIGN.md` exists in this role.
User chose **Keep**. No diff was applied. Not a gap, just documenting the
decision per Procedure D.

## Steps 3–13 audit — one fix applied, everything else already compliant

* **Step 3 (fixed):** `tasks/merge_reservations.yml`'s `loop_var: subnet`
  violated `.ansible-lint`'s `loop_var_prefix: "{role_name}_"` rule.
  Renamed to `kea_dhcp_subnet` throughout the task and its
  `loop_control.label`.
* **Step 5 (meta/main.yml), Step 5b (LICENSE), Step 6 (defaults/vars
  split), Step 7 (preflight), Step 9 (molecule platform matrix/verifier),
  Step 10 (converge.yml pre_tasks), Step 13 (molecule/requirements.txt,
  collection requirements.yml):** already fully compliant or explicitly
  not applicable — this role's own CLAUDE.md locks in single-platform
  (Ubuntu Resolute 26.04 only, no OS-family branching), GPL-3.0-or-later
  (not MIT, so Step 5b's copyright-stacking doesn't apply), a single
  `defaults/main.yml` with no `vars/` split by design, and
  `ansible.builtin`-only tasks (no `requirements.yml` needed). None of
  these were changed, since changing them would contradict this role's
  own settled decisions.
* **Step 8 (README):** Requirements/Variables Reference sections already
  current. The generic template's prescribed "Task Flow" section doesn't
  exist in this README's actual structure and wasn't invented from
  scratch, per the "surgical changes" principle — flagging here rather
  than silently adding a new section.
