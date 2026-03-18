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


def test_filter_by_query_strict_package_match_when_query_includes_package():
    results = [
        _sr(
            attributes={"Resistance": "10 kOhms"},
            description="10k 0603 resistor",
            raw_data={"componentSpecificationEn": "0603"},
            mpn="A",
        ),
        _sr(
            attributes={"Resistance": "10 kOhms"},
            description="10k 0805 resistor",
            raw_data={"componentSpecificationEn": "0805"},
            mpn="B",
        ),
        _sr(
            attributes={"Resistance": "10 kOhms"},
            description="10k 0402 resistor",
            raw_data={"componentSpecificationEn": "0402"},
            mpn="C",
        ),
    ]

    filtered = SearchFilter.filter_by_query(results, "10k 0603 resistor")
    assert [r.mpn for r in filtered] == ["A"]


def test_filter_by_query_package_strictness_survives_missing_core_attributes():
    results = [
        _sr(
            attributes={},
            description="10k 0603 resistor",
            category="Thick Film Resistors - SMD",
            mpn="A",
        ),
        _sr(
            attributes={},
            description="10k 0805 resistor",
            category="Thick Film Resistors - SMD",
            mpn="B",
        ),
    ]

    filtered = SearchFilter.filter_by_query(results, "10k 0603 resistor")
    assert [r.mpn for r in filtered] == ["A"]


def test_filter_by_query_package_filter_falls_open_when_no_package_matches():
    results = [
        _sr(
            attributes={"Resistance": "10 kOhms"},
            description="10k 0805 resistor",
            raw_data={"componentSpecificationEn": "0805"},
            mpn="A",
        ),
        _sr(
            attributes={"Resistance": "10 kOhms"},
            description="10k 0402 resistor",
            raw_data={"componentSpecificationEn": "0402"},
            mpn="B",
        ),
    ]

    filtered = SearchFilter.filter_by_query(results, "10k 0603 resistor")
    assert {r.mpn for r in filtered} == {"A", "B"}


def test_sorter_prefers_lower_price_over_stock_when_relevance_equal():
    results = [
        _sr(stock_quantity=10, price="$0.20", mpn="A"),
        _sr(stock_quantity=10, price="$0.10", mpn="B"),
        _sr(stock_quantity=100, price="$1.00", mpn="C"),
    ]

    ranked = SearchSorter.rank(results)
    assert [r.mpn for r in ranked] == ["B", "A", "C"]


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


def test_sorter_prefers_requested_package_match_from_query():
    results = [
        _sr(
            mpn="A",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=2500,
            price="$0.20",
        ),
        _sr(
            mpn="B",
            category="Thick Film Resistors - SMD",
            description="10K 0805 Chip Resistor",
            stock_quantity=10000,
            price="$0.10",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10k 0603 resistor")
    assert [r.mpn for r in ranked] == ["A", "B"]


def test_sorter_filters_low_stock_passive_results_when_alternatives_exist():
    results = [
        _sr(
            mpn="LOW",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=1500,
            price="$0.01",
        ),
        _sr(
            mpn="OK",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=2500,
            price="$0.03",
        ),
        _sr(
            mpn="HIGH",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=500000,
            price="$0.02",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10k 0603 resistor")
    assert [r.mpn for r in ranked] == ["HIGH", "OK"]


def test_sorter_passive_low_stock_gate_fails_open_when_no_alternatives():
    results = [
        _sr(
            mpn="A",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=1000,
            price="$0.03",
        ),
        _sr(
            mpn="B",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=1500,
            price="$0.02",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10k 0603 resistor")
    assert [r.mpn for r in ranked] == ["B", "A"]


def test_sorter_does_not_apply_passive_stock_gate_for_inductors():
    results = [
        _sr(
            mpn="LOW",
            category="Power Inductors",
            description="10uH 0603 Inductor",
            stock_quantity=1500,
            price="$0.01",
        ),
        _sr(
            mpn="HIGH",
            category="Power Inductors",
            description="10uH 0603 Inductor",
            stock_quantity=3000,
            price="$0.02",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10uH 0603 inductor")
    assert [r.mpn for r in ranked] == ["LOW", "HIGH"]


def test_sorter_demotes_thermistors_for_resistor_query():
    results = [
        _sr(
            mpn="RES",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            stock_quantity=2500,
            price="$0.20",
        ),
        _sr(
            mpn="NTC",
            category="NTC Thermistors",
            description="10Kohms 1% NTC Thermistor 0603",
            stock_quantity=100000,
            price="$0.10",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10k 0603 resistor")
    assert [r.mpn for r in ranked] == ["RES", "NTC"]


def test_sorter_prefers_basic_part_tier_when_relevance_is_otherwise_equal():
    results = [
        _sr(
            mpn="BASE",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            raw_data={"componentLibraryType": "base"},
            stock_quantity=5000,
            price="$0.20",
        ),
        _sr(
            mpn="EXPAND",
            category="Thick Film Resistors - SMD",
            description="10K 0603 Chip Resistor",
            raw_data={"componentLibraryType": "expand"},
            stock_quantity=5000,
            price="$0.01",
        ),
    ]

    ranked = SearchSorter.rank(results, query="10k 0603 resistor")
    assert [r.mpn for r in ranked] == ["BASE", "EXPAND"]


def test_sorter_prefers_led_parts_for_led_query_over_noise():
    results = [
        _sr(
            mpn="LED0603",
            category="Standard LEDs - SMD",
            description="Green LED 0603",
            stock_quantity=5000,
            price="$0.08",
        ),
        _sr(
            mpn="NOISE-CON",
            category="Connectors: Wire To Board Connector",
            description="Green terminal connector 0603",
            stock_quantity=20000,
            price="$0.01",
        ),
        _sr(
            mpn="NOISE-SW",
            category="Switches: Switch Accessories / Caps",
            description="Green switch cap 0603",
            stock_quantity=20000,
            price="$0.01",
        ),
    ]

    ranked = SearchSorter.rank(results, query="green led 0603")
    assert [r.mpn for r in ranked] == ["LED0603", "NOISE-CON", "NOISE-SW"]
