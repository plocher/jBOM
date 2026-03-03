#!/usr/bin/env python3
"""LCSC / JLCPCB live API proof-of-concept (Issue #115).

This is a developer tool intended to be run manually (not by pytest).

Goal: Determine which Issue #115 scenario (A/B/C/D) applies by probing the
JLCPCB web search API used for SMT components.

Endpoint under test (as of 2026-03-02):
  POST https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2

Key observation:
- The response includes a taxonomy tree in `sortAndCountVoList` (category +
  subcategory names, IDs, and part counts). This is a viable alternative to a
  separate "list categories" endpoint.

Notes / constraints:
- Be conservative with load: do not run bulk catalog dumps.
- This script focuses on targeted queries and schema discovery.

What this script is expected to confirm (see #115 + #116):
- Whether unauthenticated POST works (no cookie/CSRF token required)
- Fetch page 1 of a known category + subcategory
- Fetch with attribute filters
- Confirm response schema
- Basic pagination behavior at pageSize=1024
- Basic throttling / rate limit behavior (optional probe)

POC findings (captured 2026-03-03):
- Auth: No authentication, cookies, or CSRF token required for basic searches.

Two-endpoint / two-mode pattern:
- Bootstrap/drill-down facets: `FILTER_ATTRIBUTES_URL` (filterComponentAttribute)
  - `nowCondition="productTypeIdList"` returns `data.productTypeList` (top-level categories: id, name, docCount).
  - `nowCondition="<attr>"` with `paramList=[{"parentParamName": "Resistance", "paramValueList": ["10kΩ"]}, ...]`
    returns refinement options + counts (facet groups).
- Final results: `SEARCH_URL` (selectSmtComponentList/v2)
  - Use `searchType=2` for parametric/category browse.
  - Category must be sent as `firstSortNameList: ["Resistors"]` (array).
  - Package must be sent as `componentSpecificationList: ["0603"]`.
  - Attributes must be sent as `componentAttributeList: [{"Resistance": ["10kΩ"]}, ...]`.

Taxonomy discovery:
- `sortAndCountVoList` taxonomy is returned by `selectSmtComponentList/v2` in `searchType=3` mode.
  - With `firstSortId=0` and empty `firstSortName`, this yields a global category + subcategory tree.
  - In `searchType=2` responses, `sortAndCountVoList` is not present (at least in observed calls).

Response schema confirmed (selected fields from v2 results):
- LCSC C-number: `componentCode` (e.g. "C1091")
- MPN-ish: `componentModelEn`
- Brand/manufacturer: `componentBrandEn`
- Stock: `stockCount`
- Price breaks: `componentPrices` [{startNumber,endNumber,productPrice}, ...]
- Per-result attributes list: `attributes` [{attribute_name_en, attribute_value_name}, ...]
- Product URL: `lcscGoodsUrl`
- Datasheet URL: `dataManualUrl`

Coverage note:
- The API reports `componentPageInfo.total` ≈ 7.1M parts (observed 7,102,450).
- Historic yaqwsx/jlcparts DBs are ~0.8M–1.0M rows; this mismatch is very likely a counting methodology difference
  (e.g. SKUs/variants) rather than a coverage gap.
- Therefore, Scenario A/B/C/D cannot be determined by row count alone; qualitative
  spot-checks of rare subcategories are the real test.

Stock sorting (confirmed via browser capture on 2026-03-03):
- The UI uses `sortMode="STOCK_SORT"` with `sortASC="DESC"` (or "ASC").
- `stockSort` remains `null` in those requests; attempting to set it to values like "desc" or "1" yields API `code=101`.

If you have a yaqwsx/jlcparts SQLite snapshot, pass --db to compare rough catalog
coverage (row counts + category tables) against what the live API appears to
expose.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SEARCH_URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
# This endpoint appears to return parametric attribute groupings / counts used for refinement.
# (Observed in JLCPCB frontend bundles as `/v1/componentSearch/filterComponentAttribute` under the same base.)
FILTER_ATTRIBUTES_URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/componentSearch/filterComponentAttribute"


@dataclass(frozen=True)
class AttributeFilter:
    name: str
    value: str


def _is_package_attribute_name(name: str) -> bool:
    t = (name or "").strip().lower()
    return t in {"package", "pkg", "spec", "specification"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="POC for JLCPCB/LCSC live search API (Issue #115)."
    )

    parser.add_argument(
        "--keyword",
        default="",
        help=(
            "Free-text keyword search. Leave empty to browse a category (firstSortName) without keywords."
        ),
    )

    parser.add_argument(
        "--first-sort-name",
        default="Resistors",
        help="Top-level category name (default: 'Resistors').",
    )

    parser.add_argument(
        "--first-sort-id",
        type=int,
        default=1,
        help=(
            "Top-level category numeric ID. For Resistors, 1 matches the taxonomy (and works). "
            "The sleemanj example used 23; the server appears to accept both."
        ),
    )

    parser.add_argument(
        "--second-sort-name",
        default=None,
        help="Optional subcategory name (secondSortName).",
    )

    parser.add_argument(
        "--second-sort-id",
        type=int,
        default=None,
        help="Optional subcategory numeric ID (secondSortId).",
    )

    parser.add_argument(
        "--search-type",
        type=int,
        default=2,
        help=(
            "searchType parameter. 2 is used by the JLCPCB parts UI for category/parametric browse; "
            "3 appears to be a free-text / legacy search mode."
        ),
    )

    parser.add_argument(
        "--component-library-type",
        default="null",
        choices=["null", "", "expand"],
        help=(
            "componentLibraryType parameter. Use 'null' to send JSON null (default). "
            "Some clients send '' or 'expand'."
        ),
    )

    parser.add_argument(
        "--stock-flag",
        default="null",
        choices=["null", "true", "false"],
        help="stockFlag parameter (null/true/false). Default null.",
    )

    parser.add_argument(
        "--stock-sort",
        default="null",
        help=(
            "stockSort parameter (legacy/unknown). Default null. "
            "NOTE: Browser capture indicates stock ordering is controlled by sortMode/sortASC instead."
        ),
    )

    parser.add_argument(
        "--sort-mode",
        default="",
        help=(
            "sortMode parameter (browser observed). Example: STOCK_SORT. "
            "Leave empty for server default."
        ),
    )

    parser.add_argument(
        "--sort-asc",
        default="",
        help=(
            "sortASC parameter (browser observed). Example: DESC or ASC. "
            "Leave empty for server default."
        ),
    )

    parser.add_argument(
        "--stock-sort-probe",
        action="store_true",
        help=(
            "Try browser-observed stock sorting knobs (sortMode/sortASC) and report the first page's stockCount values, "
            "to confirm stockCount-desc ordering."
        ),
    )

    parser.add_argument(
        "--print-taxonomy",
        action="store_true",
        help=(
            "Print response taxonomy (sortAndCountVoList) showing categories/subcategories + counts."
        ),
    )

    parser.add_argument(
        "--print-attribute-facets",
        action="store_true",
        help=(
            "Call filterComponentAttribute endpoint and print facet groups (attribute values + counts), if available."
        ),
    )

    parser.add_argument(
        "--product-type-id",
        action="append",
        default=[],
        help=(
            "Repeatable productTypeId values for filterComponentAttribute (sent as productTypeIdList). "
            "If omitted, defaults to --first-sort-id as a string."
        ),
    )

    parser.add_argument(
        "--presale-type",
        default="stock",
        help=(
            "presaleType for filterComponentAttribute (default: stock). "
            "This appears to control whether the facet discovery is stock-only."
        ),
    )

    parser.add_argument(
        "--facet-now-condition",
        default="",
        help=(
            "Override nowCondition for filterComponentAttribute (advanced). "
            "If empty, the script picks a heuristic based on selected filters."
        ),
    )

    parser.add_argument(
        "--probe-product-type-ids",
        type=int,
        default=0,
        help=(
            "If >0, empirically probe productTypeIdList by calling filterComponentAttribute "
            "with productTypeIdList=['1'], ['2'], ... up to N, and print any category-ish "
            "names discovered in responses."
        ),
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Current page (1-indexed).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="Page size to request (default: 20; use 1024 for max-page tests).",
    )

    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help=(
            "Package/spec filter (repeatable). Sent via componentSpecificationList. "
            "Example: --spec 0603"
        ),
    )

    parser.add_argument(
        "--attribute",
        action="append",
        default=[],
        help=(
            "Attribute filter in the form 'Name=Value'. Can be repeated. "
            "Example: --attribute 'Resistance=10kΩ'"
        ),
    )

    parser.add_argument(
        "--brand",
        action="append",
        default=[],
        help="Brand/manufacturer filter (repeatable).",
    )

    parser.add_argument(
        "--dump",
        type=Path,
        help="Optional output path to dump the raw JSON response.",
    )

    # Inventory-driven harness: iterate inventory items and issue live API queries.
    parser.add_argument(
        "--inventory-csv",
        type=Path,
        help=(
            "Run inventory-driven POC mode against a CSV inventory file (e.g. examples/SPCoast-INVENTORY.csv)."
        ),
    )
    parser.add_argument(
        "--inventory-categories",
        default="RES",
        help=(
            "Comma/space-separated inventory Category tokens to include (default: RES). "
            "Example: 'RES,CAP'."
        ),
    )
    parser.add_argument(
        "--inventory-max-items",
        type=int,
        default=10,
        help="Max number of inventory rows to query in inventory-driven mode (default: 10).",
    )
    parser.add_argument(
        "--inventory-delay-seconds",
        type=float,
        default=0.5,
        help="Delay between inventory-driven API calls (default: 0.5s).",
    )
    parser.add_argument(
        "--inventory-use-cli-category",
        action="store_true",
        help=(
            "In inventory-driven mode, do not auto-map per-row Category; instead use the "
            "CLI --first-sort-* and --second-sort-* values for every query."
        ),
    )
    parser.add_argument(
        "--inventory-use-second-sort",
        action="store_true",
        help=(
            "In inventory-driven mode, auto-select secondSort for RES based on SMD vs PTH (SMD=>Chip Resistor - Surface Mount)."
        ),
    )
    parser.add_argument(
        "--inventory-verify-lcsc",
        action="store_true",
        help=(
            "In inventory-driven mode, if the row has an LCSC C-number, report whether it appears in the returned page."
        ),
    )

    parser.add_argument(
        "--json",
        dest="use_json",
        action="store_true",
        help="Send payload as JSON (requests.post(json=...)).",
    )
    parser.add_argument(
        "--form",
        dest="use_json",
        action="store_false",
        help="Send payload as form data (requests.post(data=...)).",
    )
    parser.set_defaults(use_json=True)

    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="HTTP timeout seconds (default: 15).",
    )

    parser.add_argument(
        "--zero-results-probe",
        action="store_true",
        help="Also run a query expected to return zero results.",
    )

    parser.add_argument(
        "--mpn-probe",
        action="store_true",
        help=(
            "Also attempt an MPN lookup using the first result's MPN (if present), "
            "to see whether MPN queries work through this endpoint."
        ),
    )

    parser.add_argument(
        "--pagination-probe",
        action="store_true",
        help="Also probe pagination behavior using pageSize=1024 on pages 1 and 2.",
    )

    parser.add_argument(
        "--rate-limit-probe",
        type=int,
        default=0,
        help="If >0, perform N repeated calls to probe throttling behavior (be gentle).",
    )

    parser.add_argument(
        "--db",
        type=Path,
        help=(
            "Optional path to a yaqwsx/jlcparts SQLite DB snapshot for rough coverage comparisons. "
            "(No download logic in jBOM.)"
        ),
    )

    return parser


def _parse_attribute_filters(raw: list[str]) -> list[AttributeFilter]:
    out: list[AttributeFilter] = []
    for entry in raw:
        t = (entry or "").strip()
        if not t or "=" not in t:
            raise ValueError(
                f"Invalid --attribute entry: {entry!r} (expected Name=Value)"
            )
        name, value = t.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise ValueError(
                f"Invalid --attribute entry: {entry!r} (expected Name=Value)"
            )
        out.append(AttributeFilter(name=name, value=value))
    return out


def _g(obj: object, *keys: str, default: Any = None) -> Any:
    """Get first matching key from a dict-like object."""

    if not isinstance(obj, dict):
        return default
    for k in keys:
        if k in obj:
            return obj.get(k)
    return default


def _coerce_nullable_bool(text: str) -> bool | None:
    t = (text or "").strip().lower()
    if t in ("", "null", "none"):
        return None
    if t in ("true", "1", "yes", "y"):
        return True
    if t in ("false", "0", "no", "n"):
        return False
    raise ValueError(f"Invalid nullable boolean: {text!r}")


def _coerce_component_library_type(text: str) -> str | None:
    t = (text or "").strip()
    if t.lower() == "null":
        return None
    return t


def _build_payload(
    *,
    keyword: str,
    page: int,
    page_size: int,
    first_sort_id: int,
    first_sort_name: str,
    second_sort_id: int | None,
    second_sort_name: str | None,
    search_type: int,
    stock_flag: bool | None,
    stock_sort: str | None,
    sort_mode: str | None,
    sort_asc: str | None,
    component_library_type: str | None,
    specs: list[str],
    attributes: list[AttributeFilter],
    brands: list[str],
) -> dict[str, Any]:
    """Build a payload compatible with the v2 endpoint.

    Notes:
    - The JLCPCB parts UI appears to use `searchType=2` and sends category as
      `firstSortNameList` (array) rather than only `firstSortName`.
    - Package (e.g. 0603) is sent via `componentSpecificationList`.
    - Parametric attributes are sent as a list of single-key dicts:
      `[{"Resistance": ["10kΩ"]}, {"Tolerance": ["1%"]}]`.

    We include both the "old" and "new" field spellings where harmless; the
    server seems to ignore unknown/extra fields.
    """

    spec_list = [str(s).strip() for s in specs if str(s).strip()]

    # Browser-observed: componentAttributeList is a list of {name: [values]}.
    grouped: dict[str, list[str]] = {}
    for f in attributes:
        if _is_package_attribute_name(f.name):
            spec_list.append(str(f.value).strip())
            continue
        key = str(f.name).strip()
        val = str(f.value).strip()
        if not key or not val:
            continue
        grouped.setdefault(key, [])
        if val not in grouped[key]:
            grouped[key].append(val)

    component_attribute_list: list[dict[str, list[str]]] = [
        {k: v} for k, v in grouped.items() if k and v
    ]

    payload: dict[str, Any] = {
        "componentAttributeList": component_attribute_list,
        "componentBrandList": [
            {"brandName": b} for b in (str(x).strip() for x in brands) if b
        ],
        "componentLibraryType": component_library_type,
        "componentSpecificationList": spec_list,
        "currentPage": int(page),
        "firstSortId": int(first_sort_id),
        "firstSortName": str(first_sort_name or ""),
        "firstSortNameList": [str(first_sort_name or "").strip()]
        if first_sort_name
        else [],
        "keyword": str(keyword or ""),
        "pageSize": int(page_size),
        "paramList": [],
        "searchSource": "search",
        "searchType": int(search_type),
        "secondSortId": second_sort_id,
        "secondSortName": second_sort_name,
        "stockSort": stock_sort,
        "stockFlag": stock_flag,
    }

    # Browser capture suggests server-side sorting is controlled by these fields.
    if sort_mode is not None and str(sort_mode).strip() != "":
        payload["sortMode"] = str(sort_mode).strip()
    if sort_asc is not None and str(sort_asc).strip() != "":
        payload["sortASC"] = str(sort_asc).strip()

    return payload


def _build_filter_component_attribute_payload(
    *,
    product_type_id_list: list[str],
    component_specification_list: list[str],
    param_list: list[dict[str, Any]],
    now_condition: str,
    presale_type: str,
    keyword: str | None,
    component_brand_list: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Build the filterComponentAttribute payload matching the Safari capture.

    Observed request shape (2026-03-02 recording):
    - top-level keys: baseQueryDto, catalogLevel, nowCondition, paramList, queryString
    - baseQueryDto includes: componentBrandList, componentSpecificationList,
      componentTypeIdList, orderLibraryTypeList, packageTypeList, filterType,
      productTypeIdList, keyword, queryShelveStatus, presaleType

    The endpoint returns `code=101` if this structure/types don't match closely.
    """

    bq: dict[str, Any] = {
        "componentBrandList": component_brand_list or [],
        "componentSpecificationList": component_specification_list,
        "componentTypeIdList": [],
        "orderLibraryTypeList": [],
        "packageTypeList": [],
        "filterType": 3,
        "productTypeIdList": product_type_id_list,
        "keyword": keyword,
        "queryShelveStatus": None,
        "presaleType": str(presale_type or "stock"),
    }

    return {
        "baseQueryDto": bq,
        "catalogLevel": 0,
        "nowCondition": str(now_condition),
        "paramList": param_list,
        "queryString": None,
    }


def _iter_string_values(obj: object) -> list[str]:
    """Collect string leaf values from an arbitrary JSON-like object."""

    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_iter_string_values(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_iter_string_values(v))
    return out


def _post(
    *,
    url: str,
    payload: dict[str, Any] | str,
    timeout: float,
    use_json: bool,
) -> tuple[int, dict[str, Any]]:
    try:
        import requests  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "This script requires 'requests'. Install it with: pip install requests"
        ) from exc

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
        if use_json
        else "application/x-www-form-urlencoded",
        "Origin": "https://jlcpcb.com",
        "Referer": "https://jlcpcb.com/parts",
        # Known-good UA from upstream examples (avoid depending on local browser versions).
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    }

    with requests.Session() as session:
        if use_json:
            resp = session.post(url, json=payload, headers=headers, timeout=timeout)
        else:
            # requests will form-encode dict values; booleans become 'True'/'False'.
            resp = session.post(url, data=payload, headers=headers, timeout=timeout)

    status = int(getattr(resp, "status_code", 0) or 0)

    try:
        data = resp.json()
    except Exception:
        text = getattr(resp, "text", "")
        raise RuntimeError(
            f"Non-JSON response (status={status}). First 200 chars: {text[:200]!r}"
        )

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object response, got {type(data).__name__}")

    return status, data


def _summarize_taxonomy(data: dict[str, Any]) -> None:
    payload = _g(data, "data", default={})
    if not isinstance(payload, dict):
        return

    tax = payload.get("sortAndCountVoList")
    if not isinstance(tax, list) or not tax:
        print("(no taxonomy found in response)")
        return

    print("\nTaxonomy (sortAndCountVoList):")
    for top in tax:
        if not isinstance(top, dict):
            continue
        name = str(top.get("sortName", "") or "").strip()
        count = top.get("componentCount")
        key_id = top.get("componentSortKeyId")
        if name:
            print(f"- {name} (id={key_id}, count={count})")
        children = top.get("childSortList")
        if isinstance(children, list):
            for child in children[:20]:
                if not isinstance(child, dict):
                    continue
                cname = str(child.get("sortName", "") or "").strip()
                ccount = child.get("componentCount")
                cid = child.get("componentSortKeyId")
                if cname:
                    print(f"  - {cname} (id={cid}, count={ccount})")
            if len(children) > 20:
                print(f"  ...(and {len(children)-20} more)")


def _first_item_fields(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "c_number": _g(item, "componentCode", "component_code", default=""),
        "mpn": _g(item, "componentModelEn", "componentModelName", "mpn", default=""),
        "brand": _g(item, "componentBrandEn", "brandName", default=""),
        "stock": _g(item, "stockCount", "stockNumber", "canPresaleNumber", default=""),
        "price": _g(item, "componentPrices", default=""),
        "desc": _g(item, "describe", "erpComponentName", "description", default=""),
        "lcsc_url": _g(item, "lcscGoodsUrl", default=""),
        "datasheet": _g(item, "dataManualUrl", default=""),
    }


def _summarize_facet_response(label: str, status: int, data: dict[str, Any]) -> None:
    print(f"\n== {label} ==")
    print(f"HTTP status: {status}")

    api_code = _g(data, "code", "status", default=None)
    api_msg = _g(data, "message", "msg", default=None)
    if api_code is not None or api_msg is not None:
        print(f"API code/message: {api_code!r} / {api_msg!r}")

    payload = _g(data, "data", default=None)
    if not isinstance(payload, dict):
        print(f"data: {type(payload).__name__}")
        return

    product_types = payload.get("productTypeList")
    if isinstance(product_types, list):
        print(f"productTypeList: {len(product_types)}")
        for it in product_types[:10]:
            if not isinstance(it, dict):
                continue
            name = it.get("name")
            key = it.get("key")
            doc = it.get("docCount")
            flag = it.get("displayFlag")
            print(f"  - {name!r} (key={key!r}, docCount={doc!r}, displayFlag={flag!r})")
        if len(product_types) > 10:
            print(f"  ...(and {len(product_types)-10} more)")

    parent_params = payload.get("parentParamList")
    if isinstance(parent_params, list):
        print(f"parentParamList: {len(parent_params)}")
        for g in parent_params[:8]:
            if not isinstance(g, dict):
                continue
            name = g.get("parentParamName") or g.get("name")
            doc = g.get("docCount")
            sub = g.get("subAggs")
            n_sub = len(sub) if isinstance(sub, list) else None
            print(f"  - {name!r} (docCount={doc!r}, subAggs={n_sub})")
        if len(parent_params) > 8:
            print(f"  ...(and {len(parent_params)-8} more)")

    # Some responses use paramList/parentParamRangeList etc.
    for k in (
        "paramList",
        "paramRangeList",
        "parentParamRangeList",
        "componentSpecificationList",
        "componentBrandList",
    ):
        v = payload.get(k)
        if isinstance(v, list):
            print(f"{k}: {len(v)}")


def _summarize_response(label: str, status: int, data: dict[str, Any]) -> None:
    print(f"\n== {label} ==")
    print(f"HTTP status: {status}")

    api_code = _g(data, "code", "status", default=None)
    api_msg = _g(data, "message", "msg", default=None)
    if api_code is not None or api_msg is not None:
        print(f"API code/message: {api_code!r} / {api_msg!r}")

    payload = _g(data, "data", default={})
    if not isinstance(payload, dict):
        print(f"data: {type(payload).__name__}")
        return

    page_info = _g(payload, "componentPageInfo", "component_page_info", default={})
    total = _g(page_info, "total", default=None)
    page_list = _g(page_info, "list", default=[])
    if isinstance(page_list, list):
        print(f"results on page: {len(page_list)}")
    print(f"total: {total!r}")

    if isinstance(page_list, list) and page_list:
        first = page_list[0] if isinstance(page_list[0], dict) else {}
        if isinstance(first, dict):
            f = _first_item_fields(first)
            print("first result (partial):")
            print(f"  C-number: {str(f['c_number']).strip()!r}")
            print(f"  MPN:      {str(f['mpn']).strip()!r}")
            print(f"  brand:    {str(f['brand']).strip()!r}")
            print(f"  stock:    {str(f['stock']).strip()!r}")

            price = f.get("price")
            if isinstance(price, (dict, list)):
                price_preview = json.dumps(price)[:120]
            else:
                price_preview = str(price)[:120]
            print(f"  price:    {price_preview!r}")

            desc = str(f.get("desc", "") or "")
            print(f"  desc:     {desc[:120]!r}")

    # Attribute filter self-description (if present)
    attr_list = _g(
        payload, "componentAttributeList", "component_attribute_list", default=[]
    )
    if isinstance(attr_list, list) and attr_list:
        print(f"attribute groups in response: {len(attr_list)}")
        for group in attr_list[:5]:
            if not isinstance(group, dict):
                continue
            name = _g(
                group,
                "attributeNameEn",
                "attribute_name_en",
                "attributeName",
                "attribute_name",
                default="",
            )
            values = _g(group, "attributeValueList", "attribute_value_list", default=[])
            if not isinstance(values, list):
                continue

            # Try to display the top few values by any available count field.
            def _count(v: object) -> int:
                if not isinstance(v, dict):
                    return 0
                raw = _g(v, "count", "qty", "total", "quantity", default=0)
                try:
                    return int(raw)
                except Exception:
                    return 0

            top = sorted(
                [v for v in values if isinstance(v, dict)], key=_count, reverse=True
            )[:3]
            top_str = []
            for v in top:
                val = _g(
                    v,
                    "attributeValueName",
                    "attribute_value_name",
                    "attributeValue",
                    "attribute_value",
                    default="",
                )
                top_str.append(f"{val}({_count(v)})")

            print(f"  {name}: {', '.join(top_str) if top_str else '(values present)'}")


def _dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _summarize_db(db_path: Path) -> None:
    print("\n== DB coverage probe ==")
    print(f"db: {db_path}")
    if not db_path.exists():
        print("DB path does not exist; skipping.")
        return

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        tables = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        print(f"tables: {tables}")

        # Print row counts for each table (best-effort; some tables may be huge).
        for t in tables:
            try:
                n = cur.execute(f"SELECT COUNT(1) FROM {t}").fetchone()[0]
            except Exception:
                n = "(error)"
            print(f"  {t}: {n}")
    finally:
        conn.close()


def _parse_inventory_categories(text: str) -> set[str]:
    raw = [
        t.strip().upper() for t in (text or "").replace(",", " ").split() if t.strip()
    ]
    return set(raw)


def _build_inventory_keyword(row: dict[str, str]) -> str:
    """Build a conservative keyword query from an inventory CSV row.

    Key idea: under-specify rather than over-specify.

    The JLCPCB search endpoint seems sensitive to vocabulary; adding free-form
    terms like "thick film" or "100mW" often collapses results to zero. This POC
    therefore prefers only the most stable, universally present tokens.
    """

    cat = (row.get("Category") or "").strip().upper()

    name = (row.get("Name") or "").strip()
    value = (row.get("Value") or "").strip()
    pkg = (row.get("Package") or "").strip()
    tol = (row.get("Tolerance") or "").strip()
    volt = (row.get("V") or "").strip()
    typ = (row.get("Type") or "").strip()

    parts: list[str] = []

    if cat == "RES":
        if not value:
            return ""
        parts.append(value)
        parts.append("ohm")
        if pkg:
            parts.append(pkg)
        if tol and tol.upper() != "N/A":
            parts.append(tol)
        return " ".join(parts).strip()

    if cat == "CAP":
        if not value:
            return ""
        parts.append(value)
        if typ:
            parts.append(typ)
        if pkg:
            parts.append(pkg)
        if tol and tol.upper() != "N/A":
            parts.append(tol)
        if volt:
            parts.append(volt)
        return " ".join(parts).strip()

    # Prefer explicit Name for IC-like categories.
    if cat in {"IC", "REG", "MCU", "OSC", "Q", "SWI"} and name:
        parts.append(name)
    elif value:
        parts.append(value)

    if pkg:
        parts.append(pkg)

    return " ".join(p for p in parts if p).strip()


def _resistor_second_sort_for_row(row: dict[str, str]) -> tuple[int | None, str | None]:
    # Known from live API taxonomy when browsing Resistors.
    smd = (row.get("SMD") or "").strip().upper()
    if smd == "SMD":
        return 2980, "Chip Resistor - Surface Mount"
    if smd == "PTH":
        return 2295, "Through Hole Resistors"
    return None, None


def _run_inventory_mode(args: argparse.Namespace) -> int:
    inv_path = Path(args.inventory_csv)
    if not inv_path.exists():
        print(f"Error: inventory file does not exist: {inv_path}", file=sys.stderr)
        return 2

    categories = _parse_inventory_categories(str(args.inventory_categories))
    max_items = max(1, int(args.inventory_max_items))
    delay = max(0.0, float(args.inventory_delay_seconds))

    with inv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = [dict(r) for r in reader if isinstance(r, dict)]

    # Deduplicate by keyword to keep load low.
    cache: dict[str, tuple[int, dict[str, Any]]] = {}

    queried = 0
    for row in rows:
        cat = (row.get("Category") or "").strip().upper()
        if cat not in categories:
            continue

        keyword = _build_inventory_keyword(row)
        if not keyword:
            continue

        # Build per-row first/second sort.
        if bool(getattr(args, "inventory_use_cli_category", False)):
            first_sort_id = int(args.first_sort_id)
            first_sort_name = str(args.first_sort_name or "")
            second_sort_id = (
                int(args.second_sort_id) if args.second_sort_id is not None else None
            )
            second_sort_name = (
                str(args.second_sort_name) if args.second_sort_name else None
            )
        else:
            # Minimal mapping for now: only RES is known-good for the POC.
            if cat != "RES":
                continue
            first_sort_id = 1
            first_sort_name = "Resistors"

            if bool(getattr(args, "inventory_use_second_sort", False)):
                second_sort_id, second_sort_name = _resistor_second_sort_for_row(row)
            else:
                second_sort_id, second_sort_name = None, None

        specs = [str(s).strip() for s in (args.spec or []) if str(s).strip()]
        if (row.get("Package") or "").strip():
            specs.append((row.get("Package") or "").strip())

        payload = _build_payload(
            keyword=keyword,
            page=1,
            page_size=int(args.page_size),
            first_sort_id=first_sort_id,
            first_sort_name=first_sort_name,
            second_sort_id=second_sort_id,
            second_sort_name=second_sort_name,
            search_type=int(args.search_type),
            stock_flag=_coerce_nullable_bool(str(args.stock_flag)),
            stock_sort=(
                None
                if str(args.stock_sort).strip().lower() in ("", "null", "none")
                else str(args.stock_sort).strip()
            ),
            sort_mode=(str(args.sort_mode).strip() or None),
            sort_asc=(str(args.sort_asc).strip() or None),
            component_library_type=_coerce_component_library_type(
                str(args.component_library_type)
            ),
            specs=specs,
            attributes=_parse_attribute_filters(list(args.attribute or [])),
            brands=list(args.brand or []),
        )

        # Cached by keyword to avoid repeating identical calls across inventory.
        if keyword in cache:
            status, data = cache[keyword]
        else:
            status, data = _post(
                url=SEARCH_URL,
                payload=payload,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            cache[keyword] = (status, data)
            if delay > 0:
                time.sleep(delay)

        ipn = (row.get("IPN") or "").strip()
        lcsc = (row.get("LCSC") or "").strip()
        print("\n== inventory row ==")
        print(f"IPN:      {ipn}")
        print(f"Category: {cat}")
        print(f"Query:    {keyword}")

        _summarize_response("inventory search", status, data)

        if bool(getattr(args, "inventory_verify_lcsc", False)) and lcsc:
            payload2 = _g(data, "data", default={})
            page_info = _g(payload2, "componentPageInfo", default={})
            lst = _g(page_info, "list", default=[])
            found = False
            if isinstance(lst, list):
                for it in lst:
                    if (
                        isinstance(it, dict)
                        and str(it.get("componentCode", "")).strip() == lcsc
                    ):
                        found = True
                        break
            print(f"LCSC expected: {lcsc}  found_in_page: {'yes' if found else 'no'}")

        queried += 1
        if queried >= max_items:
            break

    print(f"\nInventory-driven queries executed: {queried}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if getattr(args, "inventory_csv", None):
        return _run_inventory_mode(args)

    try:
        attributes = _parse_attribute_filters(list(args.attribute or []))
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    try:
        stock_flag = _coerce_nullable_bool(str(args.stock_flag))
    except Exception as exc:
        print(f"Error: invalid --stock-flag: {exc}", file=sys.stderr)
        return 2

    stock_sort = (
        str(args.stock_sort).strip() if args.stock_sort is not None else ""
    ).strip()
    if stock_sort.lower() in ("", "null", "none"):
        stock_sort_val: str | None = None
    else:
        stock_sort_val = stock_sort

    payload = _build_payload(
        keyword=str(args.keyword or ""),
        page=int(args.page),
        page_size=int(args.page_size),
        first_sort_id=int(args.first_sort_id),
        first_sort_name=str(args.first_sort_name or ""),
        second_sort_id=(
            int(args.second_sort_id) if args.second_sort_id is not None else None
        ),
        second_sort_name=(
            str(args.second_sort_name) if args.second_sort_name else None
        ),
        search_type=int(args.search_type),
        stock_flag=stock_flag,
        stock_sort=stock_sort_val,
        sort_mode=(str(args.sort_mode).strip() or None),
        sort_asc=(str(args.sort_asc).strip() or None),
        component_library_type=_coerce_component_library_type(
            str(args.component_library_type)
        ),
        specs=[str(s).strip() for s in (args.spec or []) if str(s).strip()],
        attributes=attributes,
        brands=list(args.brand or []),
    )

    status, data = _post(
        url=SEARCH_URL,
        payload=payload,
        timeout=float(args.timeout),
        use_json=bool(args.use_json),
    )
    _summarize_response("base query", status, data)

    if bool(getattr(args, "print_taxonomy", False)):
        _summarize_taxonomy(data)

    if int(getattr(args, "probe_product_type_ids", 0) or 0) > 0:
        max_id = int(args.probe_product_type_ids)
        print("\n== productTypeIdList empirical probe ==")
        for i in range(1, max_id + 1):
            pt = [str(i)]
            facet_payload = _build_filter_component_attribute_payload(
                product_type_id_list=pt,
                component_specification_list=[],
                param_list=[],
                now_condition="productTypeIdList",
                presale_type=str(args.presale_type or "stock"),
                keyword=None,
                component_brand_list=[],
            )
            st2, facets = _post(
                url=FILTER_ATTRIBUTES_URL,
                payload=facet_payload,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            api_code = _g(facets, "code", "status", default=None)
            msg = _g(facets, "message", "msg", default=None)
            # Extract any plausible category-like strings.
            strings = [s for s in _iter_string_values(facets) if isinstance(s, str)]
            hints = [
                s
                for s in strings
                if s
                and any(
                    w in s.lower()
                    for w in (
                        "resistor",
                        "capac",
                        "inductor",
                        "connector",
                        "diode",
                        "transistor",
                        "ic",
                        "integrated",
                    )
                )
            ]
            hints = list(dict.fromkeys(hints))[:5]
            hint_str = f" hints={hints!r}" if hints else ""
            print(f"  id={i:>2}: http={st2} api={api_code!r} msg={msg!r}{hint_str}")
            time.sleep(0.3)

    def _facet_call(
        *,
        pt: list[str],
        specs: list[str],
        params: list[dict[str, Any]],
        now_condition: str,
    ) -> tuple[int, dict[str, Any]]:
        facet_payload = _build_filter_component_attribute_payload(
            product_type_id_list=pt,
            component_specification_list=specs,
            param_list=params,
            now_condition=now_condition,
            presale_type=str(args.presale_type or "stock"),
            keyword=None if not str(args.keyword or "").strip() else str(args.keyword),
            component_brand_list=list(payload.get("componentBrandList") or []),
        )
        return _post(
            url=FILTER_ATTRIBUTES_URL,
            payload=facet_payload,
            timeout=float(args.timeout),
            use_json=bool(args.use_json),
        )

    if bool(getattr(args, "print_attribute_facets", False)):
        try:
            pt = [
                str(x).strip() for x in (args.product_type_id or []) if str(x).strip()
            ]
            if not pt:
                pt = [str(int(args.first_sort_id))]

            params: list[dict[str, Any]] = []
            for f in attributes:
                if _is_package_attribute_name(f.name):
                    continue
                params.append(
                    {"parentParamName": str(f.name), "paramValueList": [str(f.value)]}
                )

            specs = [str(s).strip() for s in (args.spec or []) if str(s).strip()]

            if str(args.facet_now_condition or "").strip():
                now_condition = str(args.facet_now_condition).strip()
            elif params:
                now_condition = str(params[-1]["parentParamName"])
            elif specs:
                now_condition = "componentSpecificationList"
            else:
                now_condition = "productTypeIdList"

            st2, facets = _facet_call(
                pt=pt, specs=specs, params=params, now_condition=now_condition
            )
            _summarize_facet_response(
                f"filterComponentAttribute (nowCondition={now_condition})", st2, facets
            )
        except Exception as exc:
            print(f"\n== filterComponentAttribute ==\nError: {exc}")

    if bool(getattr(args, "stock_sort_probe", False)):
        print("\n== stock sort probe ==")
        candidates: list[tuple[str, str | None, str | None]] = [
            ("baseline", None, None),
            ("STOCK_SORT DESC", "STOCK_SORT", "DESC"),
            ("STOCK_SORT ASC", "STOCK_SORT", "ASC"),
        ]

        def _top_stocks(resp: dict[str, Any], n: int = 10) -> list[int]:
            p = _g(resp, "data", default={})
            page_info = _g(p, "componentPageInfo", default={})
            lst = _g(page_info, "list", default=[])
            out: list[int] = []
            if isinstance(lst, list):
                for it in lst[:n]:
                    if not isinstance(it, dict):
                        continue
                    try:
                        out.append(int(it.get("stockCount") or 0))
                    except Exception:
                        out.append(0)
            return out

        def _is_nonincreasing(nums: list[int]) -> bool:
            return all(nums[i] >= nums[i + 1] for i in range(len(nums) - 1))

        for label, mode, asc in candidates:
            pay = dict(payload)
            # Preserve browser behavior: stockSort remains null.
            pay["stockSort"] = None
            pay["sortMode"] = mode or ""
            pay["sortASC"] = asc or ""

            st, resp = _post(
                url=SEARCH_URL,
                payload=pay,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            code = _g(resp, "code", default=None)
            stocks = _top_stocks(resp)
            ok = _is_nonincreasing(stocks) if stocks else False
            print(
                f"  {label:>14}: http={st} api={code!r} sortMode={mode!r} sortASC={asc!r} top_stocks={stocks} sorted_desc={ok}"
            )
            time.sleep(0.4)

    if args.dump:
        _dump_json(Path(args.dump), data)
        print(f"\nDumped response JSON to: {args.dump}")

    if getattr(args, "zero_results_probe", False):
        zero_payload = dict(payload)
        zero_payload["keyword"] = "__jbom__definitely_not_a_real_part__"
        st, d = _post(
            url=SEARCH_URL,
            payload=zero_payload,
            timeout=float(args.timeout),
            use_json=bool(args.use_json),
        )
        _summarize_response("zero-results query", st, d)

    if getattr(args, "mpn_probe", False):
        # Grab first result's MPN, if available.
        first_mpn = ""
        p = _g(data, "data", default={})
        page_info = _g(p, "componentPageInfo", default={})
        lst = _g(page_info, "list", default=[])
        if isinstance(lst, list) and lst and isinstance(lst[0], dict):
            first_mpn = str(
                _g(lst[0], "componentModelEn", "componentModelName", default="") or ""
            ).strip()

        if not first_mpn:
            print("\n== MPN probe ==\nNo MPN found in first result; skipping.")
        else:
            mpn_payload = dict(payload)
            mpn_payload["keyword"] = first_mpn
            st, d = _post(
                url=SEARCH_URL,
                payload=mpn_payload,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            _summarize_response(f"mpn probe (keyword={first_mpn})", st, d)

    if getattr(args, "pagination_probe", False):
        pag_payload = dict(payload)
        pag_payload["pageSize"] = 1024
        for page in (1, 2):
            pag_payload["currentPage"] = page
            st, d = _post(
                url=SEARCH_URL,
                payload=pag_payload,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            _summarize_response(f"pagination probe page={page} size=1024", st, d)

    n_calls = int(getattr(args, "rate_limit_probe", 0) or 0)
    if n_calls > 0:
        print("\n== rate limit probe ==")
        print(f"calls: {n_calls}")
        # Keep the probe gentle: sleep between calls.
        for i in range(n_calls):
            t0 = time.time()
            try:
                st, d = _post(
                    url=SEARCH_URL,
                    payload=payload,
                    timeout=float(args.timeout),
                    use_json=bool(args.use_json),
                )
                api_code = _g(d, "code", "status", default=None)
                api_msg = _g(d, "message", "msg", default=None)
                dt = time.time() - t0
                print(
                    f"  {i+1}/{n_calls}: http={st} api={api_code!r} msg={api_msg!r} dt={dt:.2f}s"
                )
            except Exception as exc:
                dt = time.time() - t0
                print(f"  {i+1}/{n_calls}: error after {dt:.2f}s: {exc}")
            time.sleep(2.0)

    if args.db:
        _summarize_db(Path(args.db))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
