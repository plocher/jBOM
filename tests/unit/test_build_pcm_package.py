"""Tests for ``scripts/build_pcm_package.py``.

Two groups of coverage live here:

* Integration smoke tests that exercise the build script with
  ``--skip-binary-fetch`` so they run without network access. They verify
  the resulting archive layout matches expectations.
* Unit tests for ``_update_metadata`` — the metadata.json sync logic that
  bumps ``versions[0].version`` and rebuilds ``download_url`` from the
  release tag pattern on every build. These tests use a scratch metadata
  file so they don't mutate the real repo-root ``metadata.json``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _import_build_module():
    """Import the build script as a module.

    ``@dataclass`` resolves type hints via ``sys.modules[cls.__module__]``
    during class construction, so the module must be registered in
    ``sys.modules`` *before* ``exec_module`` runs — otherwise the class body
    blows up with an AttributeError.
    """
    module_name = "build_pcm_package"
    spec = importlib.util.spec_from_file_location(
        module_name,
        _REPO_ROOT / "scripts" / "build_pcm_package.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


@pytest.fixture(scope="module")
def build_module():
    return _import_build_module()


def _have_all_pure_py_deps(build_module) -> bool:
    """Check that every pure-Python vendored package is importable."""
    for name in build_module._PURE_PY_VENDOR_PACKAGES:
        if importlib.util.find_spec(name) is None:
            return False
    if importlib.util.find_spec("pydantic_core") is None:
        return False
    return True


def test_read_pinned_version_returns_pydantic_core(build_module) -> None:
    """`_read_pinned_version` parses the requirements manifest correctly."""
    version = build_module._read_pinned_version("pydantic_core")
    assert version
    assert version[0].isdigit()


def test_read_pinned_version_raises_for_unknown_package(build_module) -> None:
    """Unknown packages raise a clear error rather than silently returning ''."""
    with pytest.raises(RuntimeError):
        build_module._read_pinned_version("definitely-not-a-real-package")


def test_skip_binary_fetch_build_produces_expected_layout(
    tmp_path: Path, build_module
) -> None:
    """``build(..., skip_binary_fetch=True)`` writes a PCM-shaped archive.

    Skipped when the build host does not have all pure-Python vendored
    packages installed (pure-CI environments may lack pyyaml/sexpdata).
    """
    if not _have_all_pure_py_deps(build_module):
        pytest.skip("vendored dependencies not installed on build host")

    output_dir = tmp_path / "dist"
    archive = build_module.build(output_dir, skip_binary_fetch=True)
    assert archive.is_file()

    with zipfile.ZipFile(archive, "r") as zf:
        names = set(zf.namelist())

    # Plugin adapter files
    assert "plugins/__init__.py" in names
    assert "plugins/plugin.py" in names
    assert "plugins/dialog.py" in names
    assert "plugins/options.py" in names

    # Vendored core
    assert "plugins/jbom/__init__.py" in names
    # No plugin/ recursion inside the vendored copy
    assert not any(n.startswith("plugins/jbom/plugin/") for n in names)

    # Pure-Python vendored deps
    assert any(n.startswith("plugins/pydantic/") for n in names)
    assert any(n.startswith("plugins/yaml/") for n in names)
    assert "plugins/typing_extensions.py" in names
    assert any(n.startswith("plugins/annotated_types/") for n in names)
    # Plugin __init__.py must remain the bootstrap, not be clobbered by deps.
    with zipfile.ZipFile(archive, "r") as zf:
        init_bytes = zf.read("plugins/__init__.py")
    assert b"_vendor_pydantic_core_path" in init_bytes, (
        "plugins/__init__.py appears to have been clobbered by a vendored "
        "dependency’s __init__.py"
    )

    # Compiled-deps fallback layout: plugins/_vendor/pydantic_core/<tag>/pydantic_core/...
    vendor_paths = [n for n in names if n.startswith("plugins/_vendor/pydantic_core/")]
    assert vendor_paths, "expected --skip-binary-fetch to vendor local pydantic_core"
    inner = [
        p
        for p in vendor_paths
        if "/pydantic_core/" in p[len("plugins/_vendor/pydantic_core/") :]
    ]
    assert inner, "vendored pydantic_core must contain a pydantic_core/ subdir"

    # Metadata
    assert "metadata.json" in names
    # PCM package icon for Plugin and Content Manager listing
    assert "resources/icon.png" in names
    # ActionPlugin toolbar icons (light/dark) bundled with plugin sources
    assert "plugins/assets/icons/pcb-fabrication-tool-light-24.png" in names
    assert "plugins/assets/icons/pcb-fabrication-tool-dark-24.png" in names


# ---------------------------------------------------------------------------
# _update_metadata: metadata.json version + download_url sync
# ---------------------------------------------------------------------------


def _write_metadata(
    path: Path,
    *,
    versions: list[dict] | None = None,
    homepage: str = "https://github.com/plocher/jBOM",
) -> None:
    """Write a minimal PCM-shaped metadata.json to *path*."""
    data = {
        "$schema": "https://go.kicad.org/pcm/schemas/v1",
        "name": "jBOM Fabrication",
        "identifier": "com.spcoast.jbom",
        "type": "plugin",
        "license": "MIT",
        "resources": {"homepage": homepage},
        "versions": versions if versions is not None else [],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _read_metadata(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_update_metadata_overwrites_stale_version_entry(
    tmp_path: Path, build_module
) -> None:
    """A stale versions[0] entry gets its version and download_url rebuilt.

    Regression guard for #338: previously ``_update_metadata`` only patched
    sha256/sizes on a *matching-version* entry, so once semantic-release
    bumped past the pinned version the manifest silently stopped updating.
    """
    meta = tmp_path / "metadata.json"
    _write_metadata(
        meta,
        versions=[
            {
                "version": "6.53.0",
                "status": "stable",
                "kicad_version": "9.0",
                "kicad_version_max": "",
                "download_url": (
                    "https://github.com/plocher/jBOM/releases/download/"
                    "pcm-v6.53.0/jbom-pcm-6.53.0.zip"
                ),
                "download_sha256": "deadbeef",
                "install_size": 111,
                "download_size": 222,
            }
        ],
    )

    build_module._update_metadata(
        "7.4.0",
        sha256="a" * 64,
        install_size=1000,
        download_size=500,
        metadata_path=meta,
    )

    entry = _read_metadata(meta)["versions"][0]
    assert entry["version"] == "7.4.0"
    assert entry["download_url"] == (
        "https://github.com/plocher/jBOM/releases/download/" "v7.4.0/jbom-pcm-7.4.0.zip"
    )
    assert entry["download_sha256"] == "a" * 64
    assert entry["install_size"] == 1000
    assert entry["download_size"] == 500


def test_update_metadata_creates_entry_when_versions_empty(
    tmp_path: Path, build_module
) -> None:
    """An empty ``versions`` list is populated with a full new-release entry."""
    meta = tmp_path / "metadata.json"
    _write_metadata(meta, versions=[])

    build_module._update_metadata(
        "7.4.0",
        sha256="b" * 64,
        install_size=42,
        download_size=21,
        metadata_path=meta,
    )

    versions = _read_metadata(meta)["versions"]
    assert len(versions) == 1
    assert versions[0]["version"] == "7.4.0"
    assert versions[0]["download_url"].endswith("/v7.4.0/jbom-pcm-7.4.0.zip")
    assert versions[0]["download_sha256"] == "b" * 64
    assert versions[0]["install_size"] == 42
    assert versions[0]["download_size"] == 21
    # Sane defaults for schema-required fields.
    assert "status" in versions[0]
    assert "kicad_version" in versions[0]


def test_update_metadata_preserves_schema_fields_on_bump(
    tmp_path: Path, build_module
) -> None:
    """``status``, ``kicad_version``, ``kicad_version_max`` are preserved."""
    meta = tmp_path / "metadata.json"
    _write_metadata(
        meta,
        versions=[
            {
                "version": "6.53.0",
                "status": "testing",
                "kicad_version": "9.0",
                "kicad_version_max": "9.99",
                "download_url": "stale",
                "download_sha256": "",
                "install_size": 0,
                "download_size": 0,
            }
        ],
    )

    build_module._update_metadata(
        "7.4.0",
        sha256="c" * 64,
        install_size=1,
        download_size=1,
        metadata_path=meta,
    )

    entry = _read_metadata(meta)["versions"][0]
    assert entry["status"] == "testing"
    assert entry["kicad_version"] == "9.0"
    assert entry["kicad_version_max"] == "9.99"


def test_update_metadata_matching_version_still_patches_sha256(
    tmp_path: Path, build_module
) -> None:
    """Backward-compat: matching version entries still get sha256/sizes patched."""
    meta = tmp_path / "metadata.json"
    _write_metadata(
        meta,
        versions=[
            {
                "version": "7.4.0",
                "status": "stable",
                "kicad_version": "9.0",
                "kicad_version_max": "",
                "download_url": (
                    "https://github.com/plocher/jBOM/releases/download/"
                    "v7.4.0/jbom-pcm-7.4.0.zip"
                ),
                "download_sha256": "",
                "install_size": 0,
                "download_size": 0,
            }
        ],
    )

    build_module._update_metadata(
        "7.4.0",
        sha256="d" * 64,
        install_size=999,
        download_size=333,
        metadata_path=meta,
    )

    entry = _read_metadata(meta)["versions"][0]
    assert entry["version"] == "7.4.0"
    assert entry["download_sha256"] == "d" * 64
    assert entry["install_size"] == 999
    assert entry["download_size"] == 333


def test_update_metadata_derives_owner_repo_from_homepage(
    tmp_path: Path, build_module
) -> None:
    """``download_url`` is derived from ``resources.homepage``.

    This portability guarantee is what lets sibling projects (e.g. kproj)
    reuse this script by simply pointing their ``resources.homepage`` at
    their own GitHub repo.
    """
    meta = tmp_path / "metadata.json"
    _write_metadata(meta, homepage="https://github.com/example-org/kproj")

    build_module._update_metadata(
        "1.2.3",
        sha256="e" * 64,
        install_size=1,
        download_size=1,
        metadata_path=meta,
        archive_name_template="kproj-pcm-{version}.zip",
    )

    entry = _read_metadata(meta)["versions"][0]
    assert entry["download_url"] == (
        "https://github.com/example-org/kproj/releases/download/"
        "v1.2.3/kproj-pcm-1.2.3.zip"
    )


def test_update_metadata_accepts_version_only_call(
    tmp_path: Path, build_module
) -> None:
    """Called with only ``version=``, the entry is rewritten with placeholder hash/sizes.

    Used by the workflow's two-phase update: (1) bump version+URL before
    the archive is staged so the archived ``metadata.json`` carries the
    new version, then (2) after zipping, patch sha256/sizes.
    """
    meta = tmp_path / "metadata.json"
    _write_metadata(
        meta,
        versions=[
            {
                "version": "6.53.0",
                "status": "stable",
                "kicad_version": "9.0",
                "kicad_version_max": "",
                "download_url": "stale",
                "download_sha256": "deadbeef",
                "install_size": 111,
                "download_size": 222,
            }
        ],
    )

    build_module._update_metadata("7.4.0", metadata_path=meta)

    entry = _read_metadata(meta)["versions"][0]
    assert entry["version"] == "7.4.0"
    assert entry["download_url"].endswith("/v7.4.0/jbom-pcm-7.4.0.zip")
    # Hash/sizes reset — they are re-populated by the post-zip second call.
    assert entry["download_sha256"] == ""
    assert entry["install_size"] == 0
    assert entry["download_size"] == 0
