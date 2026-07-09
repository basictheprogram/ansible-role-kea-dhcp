# TODO — ansible-sync-role session (2026-07-08)

Items flagged during the sync but not resolved in this session.

## 1. `.pre-commit-config.yaml` — write blocked, apply by hand

Cowork blocked `Write`/`Edit` on this file with "resolves to a protected
location" (known, reproducible issue — see the ansible-sync-role skill's
`references/known-issues.md`, no workaround exists). The user chose
"Overwrite" with the template version during Step 1. Apply this diff by hand
(from repo root):

```diff
--- .pre-commit-config.yaml (current)
+++ .pre-commit-config.yaml (template — overwrite chosen)
@@ -8,16 +8,12 @@
       - id: trailing-whitespace
       - id: end-of-file-fixer
       - id: check-yaml
-        args: ["--unsafe"]
-      - id: check-merge-conflict
-      - id: mixed-line-ending
-        args: ["--fix=lf"]
       - id: check-added-large-files
         args: ["--maxkb=600"]
       - id: detect-private-key
-      - id: check-symlinks
+      - id: check-shebang-scripts-are-executable
       - id: file-contents-sorter
-        files: \.gitignore$
+        files: requirements.txt|\.gitignore|\.dockerignore

   - repo: https://github.com/adrienverge/yamllint.git
     rev: v1.38.0
@@ -32,6 +28,28 @@
     hooks:
       - id: gitleaks

+  - repo: https://github.com/astral-sh/ruff-pre-commit
+    rev: v0.15.16
+    hooks:
+      - id: ruff
+        name: Ruff check
+        description: "Run 'ruff check' for extremely fast Python linting"
+        args: [--fix]
+
+      - id: ruff-format
+        name: Ruff format
+        description: "Run 'ruff format' for extremely fast Python formatting"
+
+  - repo: https://github.com/hadolint/hadolint
+    rev: v2.14.0
+    hooks:
+      - id: hadolint
+        name: Lint Dockerfiles
+        description: Runs hadolint to lint Dockerfiles
+        language: system
+        types: ["dockerfile"]
+        entry: hadolint
+
   - repo: local
     hooks:
       - id: ansible-lint
@@ -40,3 +58,25 @@
         entry: ansible-lint
         files: \.(yaml|yml)$
         pass_filenames: false
+
+  - repo: https://github.com/jumanjihouse/pre-commit-hooks
+    rev: 3.0.0
+    hooks:
+      # - id: bundler-audit
+      # - id: check-mailmap
+      # - id: fasterer
+      # - id: forbid-binary
+      # - id: forbid-space-in-indent
+      # - id: git-check  # Configure in .gitattributes
+      # - id: git-dirty  # Configure in .gitignore
+      # - id: markdownlint # Configure in .mdlrc
+      # - id: reek
+      # - id: require-ascii
+      # - id: rubocop
+      # - id: script-must-have-extension
+      # - id: script-must-not-have-extension
+      - id: shellcheck
+      - id: shfmt
+
+ci:
+  autoupdate_schedule: weekly
```

Note: the template's `hadolint` hook lints Dockerfiles, and this role has
none — it'll simply never match any files. Harmless, but worth knowing it's
inert here.

## 2. `.ansible-lint` — unused mock_roles/mock_modules

Per the user's explicit "Overwrite" choice in Step 1, `.ansible-lint` now
carries the template's `mock_roles: [jborean93.win_openssh]` and
`mock_modules:` list (Docker/Windows/Chocolatey modules). This role uses
none of them — they're inert, not harmful, but a future cleanup pass could
trim them to just what this role actually needs.

## 3. `.github/workflows/molecule.yml` looks possibly redundant/dead

`.github/workflows/ci.yml` already has its own `molecule` job (runs
`molecule test`, no matrix). `.github/workflows/molecule.yml` is a second,
separate workflow that runs `molecule test --all` on push/PR to
main/master, using a `matrix.distro`/`matrix.image` strategy that sets
`MOLECULE_DISTRO`/`MOLECULE_IMAGE` env vars — but neither
`molecule/default/molecule.yml` nor `molecule/ddns/molecule.yml` actually
reads those env vars (both hardcode
`geerlingguy/docker-ubuntu2604-ansible:latest` directly). This means the
matrix strategy is currently a no-op — it always runs the same fixed image
regardless of what the matrix would set. Investigate whether
`molecule.yml` should be removed (duplicate of `ci.yml`'s job) or fixed to
actually parameterize the scenario platforms. Out of scope for this sync
(Procedure B only covers legacy CI systems, not auditing GitHub Actions
logic) — not touched.

## 4. CLAUDE.md's role file structure listing omits `tasks/pre-flight.yml`

Pre-existing gap, not introduced by this session — the `tasks/` block in
CLAUDE.md's "Role File Structure" section lists `main.yml`, `deploy_dhcp.yml`,
`deploy_ddns.yml`, `key_management.yml` but not `pre-flight.yml` (which does
exist and is wired in as the first task in `tasks/main.yml`). Left as-is per
"surgical changes, mention don't silently fix" — flagging here since this
document is otherwise being kept as the source of truth.

## 5. `meta/argument_specs.yml` — skipped by user decision

No `meta/argument_specs.yml` exists. User chose "Skip" — not required by any
enabled `.ansible-lint` rule, and README's Variables Reference already
documents all ~40 `defaults/main.yml` keys. Revisit if `argument_specs`
schema validation becomes a project requirement later.
