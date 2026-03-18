from jbom.services.search.query_shaping import (
    expand_led_color_token,
    shape_search_query,
)


def test_expand_led_color_token_handles_shorthand() -> None:
    assert expand_led_color_token("G") == "green"
    assert expand_led_color_token("ir") == "infrared"
    assert expand_led_color_token("green") == "green"


def test_shape_search_query_led_intent_adds_led_specific_tokens() -> None:
    shaped = shape_search_query("led green 0603")
    lowered = shaped.lower().split()
    assert "led" in lowered
    assert "green" in lowered
    assert "0603" in lowered
    assert "smd" in lowered
    assert "indicator" in lowered


def test_shape_search_query_led_category_expands_color_alias() -> None:
    shaped = shape_search_query("g 0603", category="LED", package="0603")
    lowered = shaped.lower().split()
    assert "green" in lowered
    assert "led" in lowered
    assert "smd" in lowered
    assert "indicator" in lowered
