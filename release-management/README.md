# Release-Artifact Naming Contract

This document is the source of truth for what artifacts every jBOM release
attaches and where consumers can find them. The release automation in
[`.github/workflows/semantic-release.yml`](../.github/workflows/semantic-release.yml)
and the PCM archive builder in
[`scripts/build_pcm_package.py`](../scripts/build_pcm_package.py) must
uphold this contract on every release.

## Release tag naming

Semantic-release cuts every release with a plain `vX.Y.Z` tag (e.g.
`v7.4.0`). There is no separate PCM tag prefix — the same tag anchors
the PyPI publish and the PCM archive. Historic `pcm-vX.Y.Z` tags are
retained but no longer produced.

## Attached assets

Every release produced by the automation attaches four files:

| Asset | Purpose | Consumer |
|---|---|---|
| `jbom-pcm-<VERSION>.zip` | Canonical, versioned PCM archive | KiCad PCM (via download_url in `metadata.json`) |
| `jbom-pcm.zip` | Byte-identical copy of the versioned archive under a stable filename | End-users installing via `releases/latest/download/jbom-pcm.zip` |
| `jbom-<VERSION>-py3-none-any.whl` | PyPI wheel, mirror-attached to VCS release | Developers auditing a specific release's shipped bits |
| `jbom-<VERSION>.tar.gz` | PyPI sdist, mirror-attached to VCS release | Same |

The two PCM archives (`jbom-pcm-<VERSION>.zip` and `jbom-pcm.zip`) are
byte-identical. The stable-name copy exists so that
`https://github.com/plocher/jBOM/releases/latest/download/jbom-pcm.zip`
resolves to the newest release without any per-release maintenance —
GitHub resolves the `releases/latest/download/<asset>` URL to whatever
asset of that name is attached to the newest published release.

## Manifest file

`metadata.json` at the repo root is the KiCad PCM manifest for jBOM.
Its `versions[0]` entry is rewritten on every release with:

- `version` — matching the release version
- `download_url` —
  `https://github.com/plocher/jBOM/releases/download/v<VERSION>/jbom-pcm-<VERSION>.zip`
  (versioned; PCM requires this)
- `download_sha256` — SHA-256 of the built PCM archive
- `install_size` — uncompressed installed size in bytes
- `download_size` — compressed archive size in bytes

Consumers reading the manifest directly should fetch it from
`https://raw.githubusercontent.com/plocher/jBOM/main/metadata.json`.
The release workflow commits the updated manifest back to `main` after
attaching the release assets so this URL stays authoritative.

A copy of `metadata.json` also ships inside every PCM archive at the
archive root. That in-archive copy carries the correct version and
download_url but placeholder hash/size fields, because the hash is
computed over the archive itself. KiCad reads the authoritative hash
from the manifest, not from inside the archive.

## Consumer URLs

End-user install (via KiCad PCM):

```
https://github.com/plocher/jBOM/releases/latest/download/jbom-pcm.zip
```

Versioned direct download (for reproducible builds, audits, manifest
references):

```
https://github.com/plocher/jBOM/releases/download/vX.Y.Z/jbom-pcm-X.Y.Z.zip
```

Manifest (for third-party PCM registries, mirrors, or CI checks):

```
https://raw.githubusercontent.com/plocher/jBOM/main/metadata.json
```

## Automation pipeline

The pipeline lives in a single job in
[`.github/workflows/semantic-release.yml`](../.github/workflows/semantic-release.yml).
It fires on every push to `main` and runs these steps in order (all
release-only steps are gated on `dist/` being non-empty after
`semantic-release version`, which is the reliable signal that a new
version was actually cut):

1. `semantic-release version` — determines the next version from
   Conventional Commits, updates `pyproject.toml` + `src/jbom/__init__.py`,
   regenerates `CHANGELOG.md`, tags, and pushes.
2. **Detect release** — inspects `dist/` and reads the new version from
   `pyproject.toml` for use by later steps.
3. **Publish to PyPI** — twine-uploads only `dist/*.whl` and
   `dist/*.tar.gz`. The PCM archive is intentionally excluded from PyPI.
4. **Install vendored runtime deps** — `pip install -r scripts/_vendor_requirements.txt`
   so the PCM builder can find pure-Python packages via `importlib.util.find_spec`.
5. **Build PCM archive and sync `metadata.json`** — runs
   `python scripts/build_pcm_package.py --update-metadata`, which (a)
   bumps `versions[0].version` and `download_url` before the archive is
   staged so the archived manifest carries the new version, and (b)
   patches `download_sha256` / `install_size` / `download_size` into the
   repo-root manifest after zipping. A stable-name copy is made with
   `cp dist/jbom-pcm-<VERSION>.zip dist/jbom-pcm.zip`.
6. **Attach release assets** — `gh release upload` with `--clobber`
   attaches the versioned PCM archive, the stable-name copy, and the
   PyPI wheel + sdist to the `vX.Y.Z` release. `--clobber` makes the
   step idempotent for workflow re-runs.
7. **Sync `metadata.json` back to `main`** — commits the patched
   manifest with `[skip ci]` in the subject line so the push does not
   re-trigger the release workflow. Skipped when `metadata.json` did
   not change (safety net).

The `[skip ci]` marker is honored by GitHub Actions and prevents the
follow-up commit from cascading into another release run. See
[GitHub docs on skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs/skipping-workflow-runs).

## Failure modes and recovery

- **Workflow fails after PyPI publish, before asset attach.** PyPI is
  irrevocable, so a subsequent manual invocation must skip that step.
  Rerun the workflow with the release-only steps and let `--clobber`
  overwrite any partial uploads.
- **`metadata.json` sync push race.** If another commit lands on `main`
  between the workflow's fetch and its `git push`, the push fails.
  Re-run the workflow — the second attempt refreshes and re-computes,
  and `--clobber` makes the asset attach idempotent.
- **`metadata.json` has drifted manually.** The next release will
  overwrite `versions[0]` regardless of prior content; drift is
  self-healing.

## Portability notes

The PCM archive contract described here is specific to jBOM, but the
mechanics are reusable by sibling KiCad-plugin projects (e.g. `kproj`)
that follow the same conventions:

- `metadata.json` at the repo root, with `resources.homepage` pointing
  at the project's GitHub URL.
- `scripts/build_pcm_package.py` (or an equivalent vendored copy)
  accepting the same `--update-metadata` flag and its
  `archive_name_template` argument.
- Semantic-release-driven `vX.Y.Z` tagging.

`_update_metadata` in the builder derives the `download_url` owner /
repo from `resources.homepage`, so the same code produces correct URLs
for any repo following the shape. The archive filename template is a
parameter, so `kproj-pcm-{version}.zip` is a one-line change.

## Related documents

- [`release-management/WARP.md`](WARP.md) — semantic-release
  operational guidance, secrets, and pre-commit rules.
- [`release-management/version-management.md`](version-management.md) —
  version-file layout and the single-source-of-truth rule.
- [`release-management/github-secrets-setup.md`](github-secrets-setup.md)
  — required secrets (`GITHUB_TOKEN`, `PYPI_API_TOKEN`).
- Root [`README.md`](../README.md) — end-user PCM install instructions.
