from jbom.services.search.heuristic_signals import (
    evaluate_relevance_signals,
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


def test_signal_evaluator_aggregates_named_contributions():
    result = _sr()
    evaluation = evaluate_relevance_signals(
        result,
        evaluators=(
            ("a", lambda _r: 3),
            ("b", lambda _r: -1),
            ("c", lambda _r: 0),
        ),
    )

    assert evaluation.score == 2
    assert [(signal.key, signal.contribution) for signal in evaluation.signals] == [
        ("a", 3),
        ("b", -1),
    ]


def test_signal_evaluator_can_include_zero_contributions():
    result = _sr()
    evaluation = evaluate_relevance_signals(
        result,
        evaluators=(
            ("a", lambda _r: 0),
            ("b", lambda _r: 1),
        ),
        include_zero_contributions=True,
    )

    assert [(signal.key, signal.contribution) for signal in evaluation.signals] == [
        ("a", 0),
        ("b", 1),
    ]


def test_signal_to_dict_is_json_serializable():
    result = _sr()
    evaluation = evaluate_relevance_signals(
        result,
        evaluators=(("a", lambda _r: 4),),
    )

    assert evaluation.signals[0].to_dict() == {"key": "a", "contribution": 4}
