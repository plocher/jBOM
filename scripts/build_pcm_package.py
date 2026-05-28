#!/usr/bin/env python3
"""Build a PCM-compliant KiCad plugin archive for jBOM.

Usage::

    python scripts/build_pcm_package.py [--output-dir dist/] [--update-metadata]
        [--skip-binary-fetch]

Produces::

    dist/jbom-pcm-{version}.zip   — the PCM-installable archive

PCM archive layout (per KiCad addon spec)::

    Archive root/
      plugins/
        __init__.py          ← guard + registration (from src/jbom/plugin/)
        plugin.py
        dialog.py
        options.py
        jbom/                ← vendored jbom core (src/jbom/ minus plugin/)
        sexpdata.py          ← vendored (single-file module)
        yaml/                ← vendored PyYAML package
        pydantic/            ← vendored pure-Python Pydantic package
        typing_extensions.py ← vendored typing_extensions module
        annotated_types/     ← vendored annotated_types package
        typing_inspection/   ← vendored typing_inspection package
        _vendor/
          pydantic_core/
            cp39-macosx_arm64/pydantic_core/...
            cp39-macosx_x86_64/pydantic_core/...
            cp39-manylinux_x86_64/pydantic_core/...
            cp39-manylinux_aarch64/pydantic_core/...
            cp39-win_amd64/pydantic_core/...
            cp312-...
      resources/
        icon.png             ← 64×64 PNG for PCM manager
      metadata.json

The ``plugins/`` directory is what KiCad adds to ``sys.path`` when loading the
plugin. ``src/jbom/plugin/__init__.py`` inspects ``sys.version_info`` and
``platform.machine()`` at load time and prepends the matching
``_vendor/pydantic_core/<tag>/`` directory to ``sys.path`` so the compiled
extension that matches the active KiCad Python interpreter is the one that
gets imported.

Flags
-----
--output-dir DIR
    Directory where the zip is written (default: ``dist/``).
--update-metadata
    After building, patch ``metadata.json`` in the repo root with the computed
    ``download_sha256``, ``install_size``, and ``download_size`` for the
    current version.  Useful when preparing a release.
--skip-binary-fetch
    Do not call ``pip download`` for compiled deps; only vendor the build
    host's local pydantic_core.  Useful for offline CI smoke tests and for
    fast iteration on the script itself.  The resulting archive is *not*
    suitable for distribution.

Design notes
------------
This script uses only the Python standard library plus ``pip`` invoked as a
subprocess.  No third-party build-system plugin.  Migration to
``hatch-kicad`` later is straightforward: the archive layout produced here is
fully declarative.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo layout constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.resolve()
_SRC_JBOM = _REPO_ROOT / "src" / "jbom"
_PLUGIN_SRC = _SRC_JBOM / "plugin"
_METADATA_SRC = _REPO_ROOT / "metadata.json"
_RESOURCES_SRC = _REPO_ROOT / "resources"  # may not exist yet

# Subdirectories of src/jbom/ to include in the vendored jbom/ copy.
# The plugin/ subdirectory is excluded to avoid recursion.
_JBOM_INCLUDE_SUBDIRS = [
    "application",
    "cli",
    "common",
    "config",
    "services",
    "suppliers",
    "workflows",
    "sch_api",
]

# Top-level files in src/jbom/ to include (e.g. __init__.py, __main__.py).
_JBOM_INCLUDE_ROOT_FILES = [
    "__init__.py",
    "__main__.py",
]

# Glob patterns for files to skip when copying (matched against each file name).
_SKIP_FILENAMES: set[str] = {".DS_Store", ".gitignore"}
# Skip compiled extension binaries by default.
_SKIP_SUFFIXES: tuple[str, ...] = (".pyc", ".so", ".pyd")

# Pure-Python packages to vendor once from the build host.
# Keys are import names; values control how to vendor them.
#
# WARNING: ``single_file: True`` may only be used when ``spec.origin`` points
# at a file *not* named ``__init__.py``; otherwise it would clobber the
# plugin's own ``plugins/__init__.py`` when copied into the staging directory.
_PURE_PY_VENDOR_PACKAGES = {
    "sexpdata": {"single_file": True},  # sexpdata.py
    "yaml": {"single_file": False},  # yaml/ package directory (PyYAML)
    "pydantic": {"single_file": False},
    "typing_extensions": {"single_file": True},  # typing_extensions.py
    "annotated_types": {"single_file": False},  # annotated_types/ package dir
    "typing_inspection": {"single_file": False},
}

_VENDOR_REQUIREMENTS_FILE = _REPO_ROOT / "scripts" / "_vendor_requirements.txt"


@dataclass(frozen=True)
class _BinaryTarget:
    """One (python, platform, abi) combo for compiled-dep vendoring."""

    python_version: str  # e.g. "3.9"
    abi: str  # e.g. "cp39"
    platform_tag: str  # pip's --platform value, e.g. "manylinux2014_x86_64"
    folder_tag: str  # vendor folder name, e.g. "cp39-manylinux_x86_64"


# Targets matched to KiCad releases (cp39 for KiCad 9, cp312 for KiCad 10).
_BINARY_TARGETS: tuple[_BinaryTarget, ...] = (
    # KiCad 9 — CPython 3.9
    _BinaryTarget("3.9", "cp39", "macosx_11_0_arm64", "cp39-macosx_arm64"),
    _BinaryTarget("3.9", "cp39", "macosx_10_12_x86_64", "cp39-macosx_x86_64"),
    _BinaryTarget("3.9", "cp39", "manylinux2014_x86_64", "cp39-manylinux_x86_64"),
    _BinaryTarget("3.9", "cp39", "manylinux2014_aarch64", "cp39-manylinux_aarch64"),
    _BinaryTarget("3.9", "cp39", "win_amd64", "cp39-win_amd64"),
    # KiCad 10 — CPython 3.12
    _BinaryTarget("3.12", "cp312", "macosx_11_0_arm64", "cp312-macosx_arm64"),
    _BinaryTarget("3.12", "cp312", "macosx_10_12_x86_64", "cp312-macosx_x86_64"),
    _BinaryTarget("3.12", "cp312", "manylinux2014_x86_64", "cp312-manylinux_x86_64"),
    _BinaryTarget("3.12", "cp312", "manylinux2014_aarch64", "cp312-manylinux_aarch64"),
    _BinaryTarget("3.12", "cp312", "win_amd64", "cp312-win_amd64"),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_skip(path: Path, *, include_binary_extensions: bool = False) -> bool:
    """Return True if *path* should be excluded from the archive."""
    if include_binary_extensions and path.suffix in {".so", ".pyd"}:
        return (
            path.name in _SKIP_FILENAMES
            or path.name == "__pycache__"
            or any(part == "__pycache__" for part in path.parts)
        )
    return (
        path.name in _SKIP_FILENAMES
        or path.suffix in _SKIP_SUFFIXES
        or path.name == "__pycache__"
        or any(part == "__pycache__" for part in path.parts)
    )


def _copy_tree_filtered(
    src: Path, dst: Path, *, include_binary_extensions: bool = False
) -> int:
    """Recursively copy *src* to *dst*, skipping junk files.

    Returns the total uncompressed byte count copied.
    """
    total_bytes = 0
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if _should_skip(item, include_binary_extensions=include_binary_extensions):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            total_bytes += item.stat().st_size
    return total_bytes


def _vendor_package(
    name: str,
    single_file: bool,
    dest_dir: Path,
    *,
    include_binary_extensions: bool = False,
) -> int:
    """Copy a vendored package into *dest_dir*.

    For single-file packages (e.g. ``sexpdata``), copies ``sexpdata.py``.
    For package directories (e.g. ``yaml``), copies the whole directory.

    Returns the total uncompressed byte count copied.
    """
    spec = importlib.util.find_spec(name)
    if spec is None:
        print(
            f"  WARNING: package {name!r} not found in current environment; skipping vendor step.",
            file=sys.stderr,
        )
        return 0

    if single_file:
        # e.g. sexpdata.py — spec.origin is the file path
        origin = Path(spec.origin)
        if origin.name == "__init__.py":
            raise RuntimeError(
                f"Package {name!r} is registered as single_file but resolves to "
                f"{origin}; that would overwrite plugins/__init__.py. Mark it as "
                "single_file: False in _PURE_PY_VENDOR_PACKAGES."
            )
        target = dest_dir / origin.name
        shutil.copy2(origin, target)
        size = origin.stat().st_size
        print(f"  vendored {name} ({origin.name}, {size:,} bytes)")
        return size
    else:
        # Package directory — spec.submodule_search_locations[0] is the dir
        locs = list(spec.submodule_search_locations or [])
        if not locs:
            print(
                f"  WARNING: cannot locate package directory for {name!r}; skipping.",
                file=sys.stderr,
            )
            return 0
        pkg_dir = Path(locs[0])
        target_dir = dest_dir / name
        size = _copy_tree_filtered(
            pkg_dir,
            target_dir,
            include_binary_extensions=include_binary_extensions,
        )
        print(f"  vendored {name}/ ({size:,} bytes uncompressed)")
        return size


def _read_pinned_version(package: str) -> str:
    """Return the pinned version of *package* from _vendor_requirements.txt."""
    if not _VENDOR_REQUIREMENTS_FILE.is_file():
        raise RuntimeError(
            f"Missing pinned vendor requirements file at {_VENDOR_REQUIREMENTS_FILE}"
        )
    needle = package.lower().replace("-", "_")
    for raw in _VENDOR_REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line:
            continue
        name, _, version = line.partition("==")
        if name.strip().lower().replace("-", "_") == needle:
            return version.strip()
    raise RuntimeError(
        f"Package {package!r} is not pinned in {_VENDOR_REQUIREMENTS_FILE}"
    )


def _extract_wheel_package(wheel_path: Path, package_name: str, dest_dir: Path) -> int:
    """Extract the importable *package_name* directory from *wheel_path* into *dest_dir*.

    Drops ``*.dist-info`` and other non-package metadata so the vendored tree
    only contains what is needed at runtime.

    Returns the total uncompressed byte count of extracted files.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    prefix = f"{package_name}/"
    with zipfile.ZipFile(wheel_path, "r") as zf:
        for member in zf.namelist():
            if not member.startswith(prefix):
                continue
            if member.endswith("/"):
                continue
            target = dest_dir / member
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                data = src.read()
                dst.write(data)
                total_bytes += len(data)
    return total_bytes


def _pip_download(
    *,
    requirement: str,
    python_version: str,
    abi: str,
    platform_tag: str,
    dest_dir: Path,
) -> Path:
    """Run ``pip download`` for one (python, abi, platform) target.

    Returns the path to the downloaded wheel inside *dest_dir*.
    Raises ``RuntimeError`` if pip fails or no wheel is produced.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--no-deps",
        "--python-version",
        python_version,
        "--implementation",
        "cp",
        "--abi",
        abi,
        "--platform",
        platform_tag,
        "--dest",
        str(dest_dir),
        requirement,
    ]
    print(f"    pip download {requirement} ({abi}/{platform_tag})…")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"pip download failed for {requirement} ({abi}/{platform_tag}):\n"
            f"{result.stdout}\n{result.stderr}"
        )
    wheels = sorted(dest_dir.glob("*.whl"))
    if not wheels:
        raise RuntimeError(
            f"pip download produced no wheel for {requirement} ({abi}/{platform_tag})"
        )
    return wheels[-1]


def _vendor_pydantic_core_targets(plugins_dir: Path) -> int:
    """Fetch and stage pydantic_core wheels for every supported target.

    Each wheel is extracted into
    ``plugins/_vendor/pydantic_core/<folder_tag>/pydantic_core/`` so the runtime
    bootstrap can prepend the matching directory to ``sys.path``.

    Returns total uncompressed byte count.
    """
    version = _read_pinned_version("pydantic_core")
    requirement = f"pydantic_core=={version}"
    vendor_root = plugins_dir / "_vendor" / "pydantic_core"
    vendor_root.mkdir(parents=True, exist_ok=True)
    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        for target in _BINARY_TARGETS:
            target_tmp = Path(tmp) / target.folder_tag
            wheel_path = _pip_download(
                requirement=requirement,
                python_version=target.python_version,
                abi=target.abi,
                platform_tag=target.platform_tag,
                dest_dir=target_tmp,
            )
            target_out = vendor_root / target.folder_tag
            bytes_extracted = _extract_wheel_package(
                wheel_path, "pydantic_core", target_out
            )
            total += bytes_extracted
            print(f"    staged {target.folder_tag} — {bytes_extracted:,} bytes")
    return total


def _vendor_pydantic_core_local(plugins_dir: Path) -> int:
    """Fallback vendor: copy the build host's pydantic_core into _vendor.

    Used only with ``--skip-binary-fetch``.  The resulting archive will only
    work on platforms matching the build host's Python ABI / OS / CPU.
    """
    spec = importlib.util.find_spec("pydantic_core")
    if spec is None or not spec.submodule_search_locations:
        print(
            "  WARNING: pydantic_core not importable on build host; skipping local fallback.",
            file=sys.stderr,
        )
        return 0
    folder_tag = (
        f"cp{sys.version_info.major}{sys.version_info.minor}-" f"local_{sys.platform}"
    )
    target_dir = plugins_dir / "_vendor" / "pydantic_core" / folder_tag
    return _copy_tree_filtered(
        Path(list(spec.submodule_search_locations)[0]),
        target_dir / "pydantic_core",
        include_binary_extensions=True,
    )


def _zip_directory(source_dir: Path, output_zip: Path) -> int:
    """Create a zip archive of *source_dir* and return the compressed size."""
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source_dir.rglob("*")):
            if item.is_file():
                arcname = item.relative_to(source_dir)
                zf.write(item, arcname)
    return output_zip.stat().st_size


def _sha256_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of *path*."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_version() -> str:
    """Read __version__ from src/jbom/__init__.py without importing the package."""
    init_py = _SRC_JBOM / "__init__.py"
    for line in init_py.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            # e.g.  __version__ = "6.53.0"
            _, _, rhs = line.partition("=")
            return rhs.strip().strip('"').strip("'")
    raise RuntimeError(f"Cannot read __version__ from {init_py}")


def _update_metadata(
    version: str,
    sha256: str,
    install_size: int,
    download_size: int,
) -> None:
    """Patch the repo-root metadata.json with computed release values."""
    data = json.loads(_METADATA_SRC.read_text(encoding="utf-8"))
    for v in data.get("versions", []):
        if v.get("version") == version:
            v["download_sha256"] = sha256
            v["install_size"] = install_size
            v["download_size"] = download_size
    _METADATA_SRC.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  updated metadata.json with sha256={sha256[:16]}…")


# ---------------------------------------------------------------------------
# Main build logic
# ---------------------------------------------------------------------------


def build(
    output_dir: Path,
    update_metadata: bool = False,
    *,
    skip_binary_fetch: bool = False,
) -> Path:
    """Build the PCM archive and return its path.

    Args:
        output_dir: Directory where the zip will be written.
        update_metadata: When True, patch repo-root metadata.json.
        skip_binary_fetch: When True, do not call ``pip download``; vendor
            only the build host's local pydantic_core.  Resulting archive is
            not distribution-ready.

    Returns:
        Path to the produced zip file.
    """
    version = _read_version()
    archive_name = f"jbom-pcm-{version}.zip"
    output_zip = output_dir / archive_name

    print(f"Building jBOM PCM archive v{version} → {output_zip}")

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "archive"
        plugins_dir = stage / "plugins"
        plugins_dir.mkdir(parents=True)

        # ------------------------------------------------------------------
        # 1. Plugin adapter files → plugins/
        # ------------------------------------------------------------------
        print("  copying plugin adapter files…")
        plugin_total = 0
        for entry in sorted(_PLUGIN_SRC.iterdir()):
            dest = plugins_dir / entry.name
            if entry.is_dir():
                plugin_total += _copy_tree_filtered(entry, dest)
            elif entry.is_file() and not _should_skip(entry):
                shutil.copy2(entry, dest)
                plugin_total += entry.stat().st_size
        print(f"    {plugin_total:,} bytes")

        # ------------------------------------------------------------------
        # 2. Vendored jbom core → plugins/jbom/
        # ------------------------------------------------------------------
        print("  vendoring jbom core…")
        jbom_vendor_dir = plugins_dir / "jbom"
        jbom_vendor_dir.mkdir()

        core_total = 0
        # Root-level files
        for fname in _JBOM_INCLUDE_ROOT_FILES:
            src_file = _SRC_JBOM / fname
            if src_file.is_file():
                shutil.copy2(src_file, jbom_vendor_dir / fname)
                core_total += src_file.stat().st_size

        # Subdirectories
        for subdir in _JBOM_INCLUDE_SUBDIRS:
            src_subdir = _SRC_JBOM / subdir
            if src_subdir.is_dir():
                core_total += _copy_tree_filtered(src_subdir, jbom_vendor_dir / subdir)

        print(f"    {core_total:,} bytes")

        # ------------------------------------------------------------------
        # 3a. Pure-Python runtime deps → plugins/
        # ------------------------------------------------------------------
        print("  vendoring pure-Python runtime dependencies…")
        vendor_total = 0
        for pkg_name, cfg in _PURE_PY_VENDOR_PACKAGES.items():
            vendor_total += _vendor_package(
                pkg_name,
                single_file=cfg["single_file"],  # type: ignore[index]
                dest_dir=plugins_dir,
            )

        # ------------------------------------------------------------------
        # 3b. Compiled deps → plugins/_vendor/<package>/<py-platform>/
        # ------------------------------------------------------------------
        if skip_binary_fetch:
            print("  vendoring pydantic_core (LOCAL ONLY — not redistributable)…")
            vendor_total += _vendor_pydantic_core_local(plugins_dir)
        else:
            print("  vendoring pydantic_core for all supported targets…")
            vendor_total += _vendor_pydantic_core_targets(plugins_dir)

        # ------------------------------------------------------------------
        # 4. metadata.json → archive root
        # ------------------------------------------------------------------
        print("  copying metadata.json…")
        shutil.copy2(_METADATA_SRC, stage / "metadata.json")

        # ------------------------------------------------------------------
        # 5. resources/ → archive root (optional)
        # ------------------------------------------------------------------
        if _RESOURCES_SRC.is_dir():
            print("  copying resources/…")
            _copy_tree_filtered(_RESOURCES_SRC, stage / "resources")
        else:
            print("  resources/ not found — skipping optional PCM icon assets")

        # ------------------------------------------------------------------
        # 6. Zip it up
        # ------------------------------------------------------------------
        print("  zipping…")
        install_size = plugin_total + core_total + vendor_total
        download_size = _zip_directory(stage, output_zip)
        sha256 = _sha256_file(output_zip)

        print()
        print(f"  archive : {output_zip}")
        print(f"  sha256  : {sha256}")
        print(f"  install : {install_size:,} bytes (uncompressed)")
        print(f"  download: {download_size:,} bytes (compressed)")

        if update_metadata:
            _update_metadata(version, sha256, install_size, download_size)

        return output_zip


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build a PCM-compliant KiCad plugin archive for jBOM.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--output-dir",
        default="dist",
        metavar="DIR",
        help="Directory to write the zip into (default: dist/)",
    )
    p.add_argument(
        "--update-metadata",
        action="store_true",
        help="Patch metadata.json with computed sha256 and sizes after build",
    )
    p.add_argument(
        "--skip-binary-fetch",
        action="store_true",
        help=(
            "Skip pip download of cross-platform pydantic_core wheels and "
            "vendor only the build host's installed copy. Resulting archive "
            "is NOT redistributable; use for local iteration only."
        ),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = (_REPO_ROOT / args.output_dir).resolve()
    try:
        build(
            output_dir,
            update_metadata=args.update_metadata,
            skip_binary_fetch=args.skip_binary_fetch,
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
