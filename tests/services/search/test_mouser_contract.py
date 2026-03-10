from __future__ import annotations

import pytest

from conftest import load_mouser_fixture
from jbom.suppliers.mouser.provider import MouserProvider


@pytest.mark.parametrize(
    "fixture_name",
    [
        "keyword_resistor_10k_0603",
        "keyword_capacitor_1uf_0805",
        "keyword_inductor_100uh",
        "keyword_connector_header",
        "empty_results",
        "error_response",
    ],
)
def test_mouser_contract_fixtures_parse_to_search_results(fixture_name: str) -> None:
    data = load_mouser_fixture(fixture_name)
    provider = MouserProvider(api_key="dummy")

    results = provider._parse_results(data)

    assert isinstance(results, list)

    for result in results:
        assert result.manufacturer
        assert result.mpn
        assert result.distributor_part_number

        assert isinstance(result.stock_quantity, int)
        assert result.stock_quantity >= 0

        assert isinstance(result.attributes, dict)


@pytest.mark.parametrize("fixture_name", ["empty_results", "error_response"])
def test_mouser_contract_empty_and_error_fixtures_return_empty_list(
    fixture_name: str,
) -> None:
    data = load_mouser_fixture(fixture_name)
    provider = MouserProvider(api_key="dummy")

    assert provider._parse_results(data) == []
