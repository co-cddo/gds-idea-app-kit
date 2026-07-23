---
marp: true
theme: uncover
paginate: true
style: |
  section {
    font-size: 24px;
  }
  h1 {
    font-size: 48px;
  }
  h2 {
    font-size: 36px;
  }
  pre {
    font-size: 18px;
  }
  table {
    font-size: 20px;
  }
---

# The `pkg` Scaffold

One command to a production-ready Python package

---

## What is it?

- A *new* command in the **`idea-app`** CLI (`gds-idea-app-kit`)
- Scaffolds Python packages under the `gds-idea-pkg-{name}` convention
- Part of the same tool that scaffolds web apps and infra

```bash
idea-app init python my-library
```

---

## What does it do?

Generates a complete, ready-to-develop package project:

```
gds-idea-pkg-my-library/
├── src/my_library/__init__.py
├── tests/conftest.py
├── pyproject.toml          # hatchling + hatch-vcs
├── .pre-commit-config.yaml # ruff, gitleaks
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml          # lint, test, build
│       └── release.yml     # auto tag + publish
├── .gitignore
├── LICENCE
└── README.md
```

---

## What you get out of the box

| Area | Detail |
|------|--------|
| Build system | hatchling + hatch-vcs (version from git tags) |
| Linting | ruff (configured in pyproject.toml) |
| Testing | pytest, CI runs across Python 3.11 – 3.14 |
| Secret scanning | gitleaks pre-commit hook |
| Dependency updates | Dependabot configured |
| CI/CD | Reusable workflows from `gds-idea-workflows-catalogue` |
| Publishing | Auto-publish to `co-cddo.github.io/gds-idea-pypi/` |

---

## Benefits

- **Standardisation** — consistent structure, tooling, and CI across all team packages
- **Ongoing updates** — `idea-app update` pushes template improvements to existing projects
- **Conflict-safe** — SHA256 manifest tracks file ownership; local edits are never silently overwritten
- **No manual versioning** — hatch-vcs derives version from git tags automatically
- **Reusable workflows** — thin orchestrator files call shared catalogue; CI improvements propagate everywhere
- **Secret scanning** — gitleaks baked in from day one

---

## How versions work

**It's fully automatic.** No more manual bumping. No more CI failures because you forgot.

Every PR merged to main → tagged → released → published to internal PyPI.

No manual steps. No intervention needed.

**Need a minor or major bump?** Add a label to your PR:

| Label | Result |
|-------|--------|
| _(none)_ | Patch: v1.0.0 → v1.0.1 |
| `bump:minor` | Minor: v1.0.0 → v1.1.0 |
| `bump:major` | Major: v1.0.0 → v2.0.0 |

No `version = "x.y.z"` anywhere in your code — `hatch-vcs` reads the git tag.

Don't need publishing? Scaffold with `--no-publish` and you just get tagging.

---

## Quick use guide

```bash
# 1. Install the CLI
idea-tools install gds-idea-app-kit
# or: uv tool install gds-idea-app-kit \
#       --index gds-idea=https://co-cddo.github.io/gds-idea-pypi/simple/

# 2. Scaffold a new package
idea-app init python my-library
# (use --no-publish if it won't be published to PyPI)

# 3. Create the repo in co-cddo and push
gh repo create co-cddo/gds-idea-pkg-my-library --public
git remote add origin ...
git push -u origin main

# 4. Develop → PR (with bump label) → merge → auto-released
```

---

## Keeping projects up to date

```bash
# Preview what would change
idea-app update --dry-run

# Apply updates
idea-app update

# Force overwrite even if you've edited managed files
idea-app update --force
```

- Locally-modified managed files get a `.new` suffix for manual review
- `tool_version` in `pyproject.toml` tracks which version last touched the project

---

## Questions?

- Repo: `co-cddo/gds-idea-app-kit`
- Internal PyPI: `co-cddo.github.io/gds-idea-pypi/`
- Docs: `docs/` directory in the repo
