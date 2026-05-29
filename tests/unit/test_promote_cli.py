"""Unit tests for ``jbom promote`` command scaffolding."""

from __future__ import annotations

import argparse
import csv
import io

import pytest

from jbom.cli.main import create_parser
from jbom.cli.promote import (
    _resolve_promote_api_key,
    _resolve_promote_supplier_context,
    handle_promote,
)


def test_promote_parser_accepts_positional_input() -> None:
    parser = create_parser()
    args = parser.parse_args(["promote", "supplier-export.csv"])

    assert args.command == "promote"
    assert args.source_inventory == "supplier-export.csv"


def test_promote_parser_accepts_api_key_argument() -> None:
    parser = create_parser()
    args = parser.parse_args(
        ["promote", "supplier-export.csv", "--api-key", "lcsc=KEY123"]
    )

    assert args.api_key == ["lcsc=KEY123"]


def test_resolve_promote_supplier_context_defaults_to_generic() -> None:
    args = argparse.Namespace(supplier=None, jlc=False)

    assert _resolve_promote_supplier_context(args) == "generic"


def test_resolve_promote_supplier_context_from_jlc_flag() -> None:
    args = argparse.Namespace(supplier=None, jlc=True)

    assert _resolve_promote_supplier_context(args) == "lcsc"


def test_resolve_promote_supplier_context_rejects_jlc_plus_supplier() -> None:
    args = argparse.Namespace(supplier=["lcsc"], jlc=True)

    with pytest.raises(ValueError, match=r"tracked by #324"):
        _resolve_promote_supplier_context(args)


def test_resolve_promote_supplier_context_rejects_multiple_suppliers() -> None:
    args = argparse.Namespace(supplier=["lcsc", "mouser"], jlc=False)

    with pytest.raises(ValueError, match=r"tracked by #324"):
        _resolve_promote_supplier_context(args)


def test_resolve_promote_supplier_context_allows_duplicate_supplier_values() -> None:
    args = argparse.Namespace(supplier=["lcsc", "LCSC", "lcsc"], jlc=False)

    assert _resolve_promote_supplier_context(args) == "lcsc"


def test_resolve_promote_api_key_accepts_matching_scoped_key() -> None:
    args = argparse.Namespace(api_key=["lcsc=KEY123"])

    assert _resolve_promote_api_key(args, supplier_context="lcsc") == "KEY123"


def test_resolve_promote_api_key_rejects_mismatched_scoped_key() -> None:
    args = argparse.Namespace(api_key=["mouser=KEY999"])

    with pytest.raises(ValueError, match=r"not present in --supplier arguments"):
        _resolve_promote_api_key(args, supplier_context="lcsc")


def test_handle_promote_stamps_supplier_context_column(tmp_path, capsys) -> None:
    source = tmp_path / "jlc-export.csv"
    source.write_text(
        '"JLC Part #","Description"\n"C2286","1uF 0603"\n',
        encoding="utf-8",
    )
    args = argparse.Namespace(
        source_inventory=str(source),
        supplier=["lcsc"],
        jlc=False,
        output="-",
        force=False,
        verbose=False,
    )

    rc = handle_promote(args)
    assert rc == 0

    output_text = capsys.readouterr().out
    reader = csv.DictReader(io.StringIO(output_text))
    rows = list(reader)

    assert reader.fieldnames is not None
    assert "SupplierContext" in reader.fieldnames
    assert rows[0]["SupplierContext"] == "lcsc"


def test_handle_promote_fails_fast_on_supplier_overlap(tmp_path, capsys) -> None:
    source = tmp_path / "jlc-export.csv"
    source.write_text(
        '"JLC Part #","Description"\n"C2286","1uF 0603"\n',
        encoding="utf-8",
    )
    args = argparse.Namespace(
        source_inventory=str(source),
        supplier=["lcsc", "mouser"],
        jlc=False,
        output="-",
        force=False,
        verbose=False,
    )

    rc = handle_promote(args)

    assert rc == 1
    assert "tracked by #324" in capsys.readouterr().err
