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


def test_handle_promote_writes_canonical_inventory_columns(tmp_path, capsys) -> None:
    source = tmp_path / "jlc-export.csv"
    source.write_text(
        '"Category","JLC Part #","MFR Part #","Footprint","Description"\n'
        '"Capacitors","C2286","CC0603KRX7R9BB104","0603","0.1uF 50V X7R \u00b110%"\n',
        encoding="utf-8",
    )
    # No --supplier / --jlc => implicit 'generic' context => no catalog
    # enrichment is attempted, keeping the test fully offline.
    args = argparse.Namespace(
        source_inventory=str(source),
        supplier=None,
        jlc=False,
        api_key=None,
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
    for column in (
        "RowType",
        "IPN",
        "Category",
        "Value",
        "Package",
        "Description",
        "MFGPN",
        "Supplier",
        "SPN",
        "Tolerance",
        "Type",
        "V",
        "Capacitance",
        "SupplierContext",
    ):
        assert column in reader.fieldnames, column

    row = rows[0]
    assert row["SupplierContext"] == "generic"
    assert row["RowType"] == "ITEM"
    assert row["Category"] == "CAP"
    assert row["Package"] == "0603"
    assert row["Value"]  # parser populated some EIA-style value
    assert row["Capacitance"]
    assert row["Tolerance"] == "10%"
    assert row["Type"] == "X7R"
    assert row["V"] == "50V"
    assert row["MFGPN"] == "CC0603KRX7R9BB104"
    assert row["SPN"] == "C2286"


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
        api_key=None,
        output="-",
        force=False,
        verbose=False,
    )

    rc = handle_promote(args)

    assert rc == 1
    assert "tracked by #324" in capsys.readouterr().err
