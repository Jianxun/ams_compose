
# analog-hub Design Review — July 23, 2025

This document captures the detailed review and iteration of the design for `analog-hub`, a dependency management tool for analog IC design libraries, optimized for open-source workflows and GitHub-centric repositories.

---

## Context and Goals

**analog-hub** aims to:
- Enable selective import of analog IP libraries from remote repositories.
- Avoid the bloat and coupling of Git submodules or full repo clones.
- Be lightweight, deterministic, and tailored for the open-source analog design community using toolchains like IIC-OSIC-TOOLS.

---

## Design Review Highlights

### ✅ Affirmed Scope
- **Open-source focus**: All flows assume open repositories (MIT, BSD, etc.), avoiding corporate VCS like Perforce or SVN.
- **GitHub ≥ 90% target**: Assumes GitHub APIs and repo layouts.
- **Large repos (e.g., PDKs)**: Should be pre-integrated in Docker containers, not managed by analog-hub.

---

## Configuration File Structure

### Original Plan
```yaml
imports:
  libA:
    repo: https://github.com/org/repo
    ref: main

exports:
  libA:
    path: libs/libA
    type: analog
```

### Revised Proposal

Use a **directory layout** under `.analog-hub/`:

```
.analog-hub/
├── imports.yaml     # consumer declarations
├── exports.yaml     # IP provider declarations
└── env.yaml         # (optional) declares required PDK/tool versions
```

**Pros:**
- Scalable as features grow (hooks, overrides, etc.)
- Allows separation of concerns (provider vs. consumer)

**Migration Support:**
- `analog-hub convert --to-multi-file` converts from `analog-hub.yaml`.

---

## Licensing & Provenance Tracking

Although open-source, license metadata still matters.

### Proposal

In `exports.yaml`:
```yaml
exports:
  my_lib:
    path: libs/my_lib
    license: MIT
    license_file: libs/my_lib/LICENSE
```

In `.analog-hub.lock`:
- Snapshot of resolved license text.
- On `update`, if license changes → raise warning.
- Require `--allow-license-change` to continue.

CLI:
```bash
analog-hub list --licenses
```

---

## Git Integration Strategy

### Assumptions
- GitHub-hosted repos.
- Consumers typically want one or two subdirectories.

### Options Compared

| Option | Pros | Cons |
|--------|------|------|
| `git clone` + sparse-checkout | Mature, flexible | Full history cloned |
| `git archive` over SSH | Minimal download | Not always supported |
| GitHub tarball endpoint | Fast, direct | GitHub only |
| PyGit2 | Precise, low-level | Extra deps, harder to maintain |

### Final Recommendation

Use GitHub tarball endpoint for >90% of cases:

```http
https://api.github.com/repos/{owner}/{repo}/tarball/{ref}
```

* Extract with `--strip-components=N`.
* Track commit SHA and warn on tag mutability.

Fallback to sparse-checkout only for niche cases.

---

## Immutable Imports & Lockfile Design

- `.analog-hub.lock` stores:
  - Resolved commit SHA
  - Path
  - License snapshot
  - Checksum

- `analog-hub update` performs:
  - Fresh clone
  - Full overwrite
  - SHA and license revalidation

Optional: flag for “editable mode” to allow local hacking.

---

## CLI Interface

| Command | Description |
|---------|-------------|
| `analog-hub install` | Pulls all `imports.yaml` IPs |
| `analog-hub update <lib>` | Fresh clone and overwrite |
| `analog-hub validate` | Validates config and lockfile |
| `analog-hub list` | Shows installed libraries |
| `analog-hub doctor` | Verifies environment (PDKs/toolchain) |

Extras:
- `--dry-run` for CI pipelines.
- `--allow-license-change` to bypass license diffs.

---

## GitHub-Specific Optimizations

| Feature | Integration |
|---------|-------------|
| Tarball download | Use for all public imports |
| `repo: user/repo` | Allow GitHub shorthand |
| GraphQL API | Use for tag/version suggestions |
| GitHub Actions | Document cache + CI validate step |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Repo tag changes SHA | Lockfile pins SHA, detect drift |
| Toolchain/P DK mismatch | `.analog-hub/env.yaml` + `analog-hub doctor` |
| API limits | Use `GITHUB_TOKEN` for CI |
| Large repos | Skip clone for PDKs; container bake-in |

---

## Next Steps

1. **Implement tarball fetch**
2. **Design import/export/lock Pydantic schemas**
3. **Build CLI MVP with Click**
4. **Test on real analog IP (e.g., `wave_view` templates)**
5. **Document: Getting Started, CI Integration, FAQ**

---

## Summary

With a clear GitHub-first and open-source-only assumption, the `analog-hub` design simplifies:
- IP fetching
- Configuration separation
- License and state tracking

These enable reproducible, maintainable analog design projects built from modular, versioned components without git bloat.

A lightweight MVP is within reach.

