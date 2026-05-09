#!/usr/bin/env python3
"""Build a PCM-compliant KiCad plugin archive for jBOM.

Usage::

    python scripts/build_pcm_package.py [--output-dir dist/] [--update-metadata]

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
          __init__.py
          application/
          cli/
          common/
          config/
          services/
          suppliers/
          workflows/
          ...
        sexpdata.py          ← vendored (single-file module)
        yaml/                ← vendored PyYAML package
      resources/
        icon.png             ← 64×64 PNG for PCM manager (TODO: add icon)
      metadata.json

The ``plugins/`` directory is what KiCad adds to ``sys.path`` when loading the
plugin, making ``import jbom``, ``import sexpdata``, and ``import yaml`` work
against the vendored copies.

Flags
-----
--output-dir DIR
    Directory where the zip is written (default: ``dist/``).
--update-metadata
    After building, patch ``metadata.json`` in the repo root with the computed
    ``download_sha256``, ``install_size``, and ``download_size`` for the
    current version.  Useful when preparing a release.

Design notes
------------
This script intentionally uses only the Python standard library (``zipfile``,
``shutil``, ``hashlib``, ``importlib``) with no third-party build-system
plugin, following Decision 3 (Y > X) agreed in issue #227.  Migration to
``hatch-kicad`` is straightforward if desired later: it produces the same
archive layout from ``pyproject.toml`` configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
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
# Skip compiled extensions (platform- and Python-version-specific binaries).
# PyYAML falls back gracefully to its pure-Python loader when the C extension
# is absent, so excluding _yaml.cpython-*.so is safe and desirable.
_SKIP_SUFFIXES: tuple[str, ...] = (".pyc", ".so", ".pyd")

# Python packages to vendor from the current environment.
# Keys are import names; values control how to vendor them.
_VENDOR_PACKAGES = {
    "sexpdata": {"single_file": True},  # sexpdata.py
    "yaml": {"single_file": False},  # yaml/ package directory (PyYAML)
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    """Return True if *path* should be excluded from the archive."""
    return (
        path.name in _SKIP_FILENAMES
        or path.suffix in _SKIP_SUFFIXES
        or path.name == "__pycache__"
        or any(part == "__pycache__" for part in path.parts)
    )


def _copy_tree_filtered(src: Path, dst: Path) -> int:
    """Recursively copy *src* to *dst*, skipping junk files.

    Returns the total uncompressed byte count copied.
    """
    total_bytes = 0
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if _should_skip(item):
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


def _vendor_package(name: str, single_file: bool, dest_dir: Path) -> int:
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
        size = _copy_tree_filtered(pkg_dir, target_dir)
        print(f"  vendored {name}/ ({size:,} bytes uncompressed)")
        return size


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


def build(output_dir: Path, update_metadata: bool = False) -> Path:
    """Build the PCM archive and return its path.

    Args:
        output_dir: Directory where the zip will be written.
        update_metadata: When True, patch repo-root metadata.json.

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
        for f in sorted(_PLUGIN_SRC.iterdir()):
            if f.is_file() and not _should_skip(f):
                dest = plugins_dir / f.name
                shutil.copy2(f, dest)
                plugin_total += f.stat().st_size
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
        # 3. Vendored runtime deps → plugins/
        # ------------------------------------------------------------------
        print("  vendoring runtime dependencies…")
        vendor_total = 0
        for pkg_name, cfg in _VENDOR_PACKAGES.items():
            vendor_total += _vendor_package(
                pkg_name,
                single_file=cfg["single_file"],  # type: ignore[index]
                dest_dir=plugins_dir,
            )

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
            print("  resources/ not found — skipping (add a 64×64 icon.png later)")

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
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = (_REPO_ROOT / args.output_dir).resolve()
    try:
        build(output_dir, update_metadata=args.update_metadata)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
