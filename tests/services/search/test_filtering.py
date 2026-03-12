from jbom.services.search.filtering import (
    SearchFilter,
    SearchSorter,
    apply_default_filters,
)
from jbom.services.search.models import SearchResult


def _sr(**kw):
    base = dict(
        manufacturer="Mfg",
        mpn="MPN",
        description="desc",
        datasheet="",
        distributor="mouser",
        distributor_part_number="123",
        availability="100 In Stock",
        price="$0.10",
        details_url="",
        raw_data={},
        lifecycle_status="Active",
        min_order_qty=1,
        category="",
        attributes={},
        stock_quantity=100,
    )
    base.update(kw)
    return SearchResult(**base)


def test_apply_default_filters_removes_out_of_stock_and_obsolete():
    results = [
        _sr(stock_quantity=0),
        _sr(lifecycle_status="Obsolete", stock_quantity=10),
        _sr(availability="Factory Order", stock_quantity=10),
        _sr(stock_quantity=10),
    ]
    filtered = apply_default_filters(results)
    assert len(filtered) == 1
    assert filtered[0].stock_quantity == 10


def test_filter_by_query_resistance_strict_matches_when_attribute_present():
    results = [
        _sr(attributes={"Resistance": "10 kOhms"}, mpn="A"),
        _sr(attributes={"Resistance": "22 kOhms"}, mpn="B"),
        _sr(attributes={}, mpn="C"),  # excluded when strict pass has matches
    ]

    filtered = SearchFilter.filter_by_query(results, "10K 0603")
    mpns = {r.mpn for r in filtered}
    assert "A" in mpns
    assert "B" not in mpns
    assert "C" not in mpns


def test_filter_by_query_backward_compat_empty_category_filters_resistance():
    results = [
        _sr(attributes={"Resistance": "10 kOhms"}, mpn="A"),
        _sr(attributes={"Resistance": "22 kOhms"}, mpn="B"),
        _sr(attributes={}, mpn="C"),  # excluded when strict pass has matches
    ]

    filtered = SearchFilter.filter_by_query(results, "10K 0603", category="")
    mpns = {r.mpn for r in filtered}
    assert "A" in mpns
    assert "B" not in mpns
    assert "C" not in mpns


def test_filter_by_query_capacitance_when_category_provided():
    results = [
        _sr(attributes={"Capacitance": "100nF"}, mpn="A"),
        _sr(attributes={"Capacitance": "1uF"}, mpn="B"),
        _sr(attributes={}, mpn="C"),  # excluded when strict pass has matches
    ]

    filtered = SearchFilter.filter_by_query(results, "100nF 0805", category="CAP")
    mpns = {r.mpn for r in filtered}
    assert "A" in mpns
    assert "B" not in mpns
    assert "C" not in mpns


def test_filter_by_query_capacitor_voltage_rating_when_present_in_query():
    results = [
        _sr(attributes={"Capacitance": "100nF", "Voltage Rating": "16V"}, mpn="A"),
        _sr(attributes={"Capacitance": "100nF", "Voltage Rating": "10V"}, mpn="B"),
        _sr(attributes={"Capacitance": "100nF"}, mpn="C"),  # fail-open for voltage
    ]

    filtered = SearchFilter.filter_by_query(results, "100nF 16V 0805", category="CAP")
    mpns = {r.mpn for r in filtered}
    assert "A" in mpns
    assert "B" not in mpns
    assert "C" in mpns


def test_filter_by_query_inductance_when_category_provided():
    results = [
        _sr(attributes={"Inductance": "100uH"}, mpn="A"),
        _sr(attributes={"Inductance": "10uH"}, mpn="B"),
        _sr(attributes={}, mpn="C"),  # excluded when strict pass has matches
    ]

    filtered = SearchFilter.filter_by_query(results, "100uH 0603", category="IND")
    mpns = {r.mpn for r in filtered}
    assert "A" in mpns
    assert "B" not in mpns
    assert "C" not in mpns


def test_filter_by_query_falls_back_to_fail_open_when_strict_pass_is_empty():
    results = [
        _sr(attributes={"Resistance": "22 kOhms"}, mpn="A"),
        _sr(attributes={"Capacitance": "100nF"}, mpn="C"),
        _sr(attributes={}, mpn="D"),
    ]

    filtered = SearchFilter.filter_by_query(results, "10K 0603")
    mpns = {r.mpn for r in filtered}
    assert "A" not in mpns
    assert "C" in mpns
    assert "D" in mpns


def test_sorter_prefers_higher_stock_then_lower_price():
    results = [
        _sr(stock_quantity=10, price="$0.20", mpn="A"),
        _sr(stock_quantity=10, price="$0.10", mpn="B"),
        _sr(stock_quantity=100, price="$1.00", mpn="C"),
    ]

    ranked = SearchSorter.rank(results)
    assert [r.mpn for r in ranked] == ["C", "B", "A"]


def test_sorter_uses_numeric_value_as_tertiary_key_when_category_provided():
    results = [
        _sr(
            stock_quantity=10,
            price="$0.10",
            mpn="A",
            attributes={"Capacitance": "1uF"},
        ),
        _sr(
            stock_quantity=10,
            price="$0.10",
            mpn="B",
            attributes={"Capacitance": "100nF"},
        ),
        _sr(
            stock_quantity=10,
            price="$0.10",
            mpn="C",
            attributes={"Capacitance": "garbage"},
        ),
    ]

    ranked = SearchSorter.rank(results, category="CAP")
    assert [r.mpn for r in ranked] == ["B", "A", "C"]
