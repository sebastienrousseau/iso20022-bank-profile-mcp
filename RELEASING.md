<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Releasing iso20022-bank-profile-mcp

This document defines **what merits a release** and **how to cut one**,
so versions are deliberate rather than ad-hoc.

## Versioning scheme

iso20022-bank-profile-mcp ships `0.0.X` and bumps the patch number on
every release; there is no lockstep with a core library, and no `1.0`
until the MCP surface is frozen (see `ROADMAP.md`). Dependency ranges
are kept aligned with the other servers of the ISO 20022 MCP Suite so
they co-install in one environment; `scripts/check_suite_consistency.py`
and the scheduled `Release Consistency` workflow fail when the tree and
PyPI disagree about which version is out.

## What merits a release

Cut a new version when there is user-visible change to ship - bug fixes,
security or dependency patches, new profiles / tools / resources /
prompts, or documentation that ships in the package.

## Pre-flight checklist

A release is ready only when **all** of the following hold on `main`:

1. `make check` is green (lint + type-check + tests at 100% line and
   branch coverage).
2. `interrogate` reports 100% docstring coverage; `mypy --strict`,
   `ruff`, `black` are clean on `iso20022_bank_profile_mcp/`, `tests/`
   and `benches/`, and `benches/bench_lint_payload.py --quick` runs.
3. Every Dependabot / CodeQL / bandit alert is resolved or has a
   documented, expiring suppression.
4. `CHANGELOG.md` has a dated section for the new version describing the
   change set (this is the single source of truth for the release).
5. The version is identical in `pyproject.toml`,
   `iso20022_bank_profile_mcp/__init__.py`, `glama.json` (including its
   Docker tag), `server.json` and the changelog (enforced by
   `scripts/verify_versions.py`, which the `Version sources agree`
   workflow runs). The Glama directory and the MCP registry read those
   two manifests; a release that forgets them shows an old version to
   every agent that browses for the server.
6. `poetry.lock` is current: the `Lockfile matches pyproject` CI job
   and the SBOM job both fail on a stale lock.
7. `requirements/*.txt` are current (`make pip-compile`): CI installs
   from the hash-pinned files, not from `pyproject.toml`.

## Cutting the release

1. Bump the version in `pyproject.toml`,
   `iso20022_bank_profile_mcp/__init__.py`, `glama.json` and
   `server.json`, and add the `CHANGELOG.md` section, in a single PR.
2. Merge the PR to `main` once CI is green.
3. Push a signed tag:

   ```bash
   git tag -s vX.Y.Z -m "iso20022-bank-profile-mcp vX.Y.Z" <merge-commit>
   git push origin vX.Y.Z
   ```

4. The tag triggers `release.yml`: it builds the distributions, runs
   `twine check`, attaches a SLSA build provenance attestation,
   publishes to PyPI through OIDC trusted publishing (with PEP 740
   attestations), signs the distributions with cosign (keyless) and
   publishes the GitHub release with the artifacts. A second job
   produces the CycloneDX and SPDX SBOMs and the licence report.
5. The same tag triggers `publish-mcp.yml`, which waits for PyPI to
   surface the version and then publishes `server.json` to the official
   MCP registry through GitHub OIDC.

## After releasing

- Confirm the version is live on
  [PyPI](https://pypi.org/project/iso20022-bank-profile-mcp/) and the
  GitHub release is published (not draft), with the SBOMs attached.
- Verify a clean install: `pip install iso20022-bank-profile-mcp==X.Y.Z`
  and `iso20022-bank-profile-mcp --version`.
- Check the [MCP registry](https://registry.modelcontextprotocol.io)
  and Glama listings show the new version.

## Optional CI integrations

These are deliberately gated so an empty / un-set secret skips the
step rather than failing the build:

- **PyPI trusted publisher** (`release.yml`): configured at
  <https://pypi.org/manage/account/publishing/>. The publisher claim
  set is `repo:sebastienrousseau/iso20022-bank-profile-mcp:environment:pypi`
  with `workflow_ref` pointing at `.github/workflows/release.yml`.
- **MCP registry publisher** (`publish-mcp.yml`): `mcp-publisher login
  github-oidc`; no secret to store.
- **Docker image**: the `Dockerfile` builds the server for a container
  deployment; images are not published by CI.
