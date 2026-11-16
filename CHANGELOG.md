# Changelog

All notable changes to this project are documented here. Versions follow semver and
must be bumped in `uos-arm64-pyqt-packaging/SKILL.md` frontmatter before re-uploading
to the WorkBuddy open platform.

## [1.0.0] - 2026-11-16

First public release. Rebuilt from a single personal note (`SKILL.md`, 5.6 KB) into a
self-contained, reusable skill package.

### Added

- `SKILL.md` rewritten with full open-platform frontmatter (`display_name`,
  `display_name_en`, `description_zh/en`, `examples_zh/en`, `version`, `author`,
  `category`, `allowed-tools`, `agent_created: true`) and a four-phase workflow with
  an explicit decision gate.
- `references/compatibility-matrix.md` — glibc / wheel / interpreter matrix, evidence
  for the four failed routes, and a reproducible `objdump -T` re-verification procedure.
- `references/migration-guide.md` — complete PyQt6 scoped-enum mapping, Python 3.7
  syntax red lines, dataclass caveats, manual review checklist.
- `references/build-and-deploy.md` — end-to-end commands, Debian 10 EOL source repair,
  deb control fields, 8-item acceptance checklist, upgrade/rollback.
- `references/troubleshooting.md` — symptom → cause → fix tables across five stages.
- `scripts/migrate_pyqt6_to_pyqt5.py` — idempotent migration with `--dry-run`,
  `--apply --backup`, `--exclude`, `--report`; token-aware so comments and string
  literals are never rewritten.
- `scripts/check_py37_compat.py` — AST gate for Python 3.7 grammar, runtime-position
  PEP 585/604 generics, missing future import, and 3.8+ stdlib APIs (`--json`, `--strict`).
- `scripts/build_deb.py` — parameterized `Architecture: all` deb builder; reads sibling
  templates, injects the sys.path bootstrap, falls back to staging-only when
  `dpkg-deb` is unavailable.
- `scripts/preflight_uos.sh` — target-machine preflight (POSIX sh).
- `scripts/fix_debian10_sources.sh` — one-shot Debian 10 EOL source repair.
- `templates/` — control, launcher, desktop, bootstrap and an example config.
- `assets/icon-512.png` — 512×512 marketplace icon (~7 KB).
- `examples/hello-pyqt5/` — before/after runnable sample.
- `tools/make_icon.py`, `tools/make_release.py` — icon generation and release
  validation (frontmatter, two-level layout, referenced resources, icon size,
  two ZIP variants, SHA256SUMS).
- Repository docs: `README.md`, `README.en.md`, `docs/PUBLISH.md`, `LICENSE`, `.gitignore`.

### Fixed / corrected relative to the original note

- Removed project-specific hard-coded paths (`源码/`, `Linux程序/`, `build_linux.sh`,
  `file-organizer`); all paths are now explicit CLI arguments.
- Added `agent_created: true` so the skill can be managed/updated by the client.
- Documented two previously missing Debian 10 traps: expired Release files
  (`Acquire::Check-Valid-Until=false`) and the vanished `buster-updates` suite.
- Documented `et-xmlfile`, openpyxl 3.1.2's transitive runtime dependency that is
  commonly lost when copying `third_party/` by hand.
- Verified openpyxl 3.1.2 against PyPI metadata: `requires_python >=3.6`, classifiers
  include Python 3.7.
- Resolved the ZIP layout ambiguity by shipping both a wrapped ZIP (client upload)
  and a flat-root ZIP (open platform submission).

### Notes

- All scripts were compiled and exercised end-to-end on Python 3.13 (migration →
  compatibility gate → staging build); `dpkg-deb` finalization still requires a Linux host.
- Marketplace submission (personal verification, original-work declaration, review)
  remains a manual step for the account owner; see `docs/PUBLISH.md`.
