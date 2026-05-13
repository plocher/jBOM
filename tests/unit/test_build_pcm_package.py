"""Integration smoke tests for ``scripts/build_pcm_package.py``.

These tests exercise the build script with ``--skip-binary-fetch`` so they
run without network access.  They verify the resulting archive layout
matches expectations:

* ``plugins/__init__.py`` and the rest of the plugin adapter are present.
* ``plugins/jbom/`` contains the vendored core (no ``plugin/`` subdir).
* Pure-Python deps live at ``plugins/<name>/`` (e.g. ``plugins/pydantic/``).
* The compiled-deps layout exists at ``plugins/_vendor/pydantic_core/<tag>/``.
* ``metadata.json`` is present at the archive root.
"""

from __future__ import annotations

import importlib.util
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
