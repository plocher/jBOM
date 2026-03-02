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

POC findings (captured 2026-03-02):
- Auth: No authentication, cookies, or CSRF token required for basic searches.
- Known-good endpoint: `SEARCH_URL` (selectSmtComponentList/v2) returns `code=200`.
- Category browse works:
  - `firstSortName`/`firstSortId` constrain the top-level category (e.g. Resistors).
  - `secondSortName`/`secondSortId` constrain subcategory (e.g. Chip Resistor - Surface Mount).
  - Response includes taxonomy tree `sortAndCountVoList` with category/subcategory IDs + counts.
- Response schema confirmed (selected fields):
  - LCSC C-number: `componentCode` (e.g. "C1091")
  - MPN-ish: `componentModelEn`
  - Brand/manufacturer: `componentBrandEn`
  - Stock: `stockCount`
  - Price breaks: `componentPrices` [{startNumber,endNumber,productPrice}, ...]
  - Per-result attributes list: `attributes` [{attribute_name_en, attribute_value_name}, ...]
  - Product URL: `lcscGoodsUrl`
  - Datasheet URL: `dataManualUrl`
- Pagination: `--pagination-probe` successfully returns 1024 results for page 1 and 2.
- Throttling: `--rate-limit-probe 5` (with built-in 2s delay) did not trigger throttling.
- Known failures / open questions:
  - Attribute filters: when `componentAttributeList` is non-empty (via `--attribute Name=Value`),
    the API returns `code=101` (unknown error). Attribute filtering is therefore NOT proven yet.
  - Attribute facet endpoint: `FILTER_ATTRIBUTES_URL` currently returns `code=500` (system error).

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
        default=3,
        help=(
            "searchType parameter. 3 is used by the known-good sleemanj example for category browsing; "
            "other values may activate different server search modes."
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
            "stockSort parameter. Default null. (POC needs to discover values for stock-desc sorting.)"
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
        "--attribute",
        action="append",
        default=[],
        help=(
            "Attribute filter in the form 'Name=Value'. Can be repeated. "
            "Example: --attribute 'Package=0603'"
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
    component_library_type: str | None,
    attributes: list[AttributeFilter],
    brands: list[str],
) -> dict[str, Any]:
    """Build a payload compatible with the v2 endpoint.

    This shape is based on reverse-engineering public clients, notably:
    - CDFER/jlcpcb-parts-database scrape script
    - PatrickWalther/go-jlcpcb-parts

    IMPORTANT: Some fields appear to be ignored by the server; we include them
    defensively to match known-working payloads.
    """

    payload: dict[str, Any] = {
        "componentAttributeList": [
            {"attributeName": f.name, "attributeValue": f.value} for f in attributes
        ],
        "componentBrandList": [
            {"brandName": b} for b in (str(x).strip() for x in brands) if b
        ],
        "componentLibraryType": component_library_type,
        "componentSpecificationList": [],
        "currentPage": int(page),
        "firstSortId": int(first_sort_id),
        "firstSortName": str(first_sort_name or ""),
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

    return payload


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
            component_library_type=_coerce_component_library_type(
                str(args.component_library_type)
            ),
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
        component_library_type=_coerce_component_library_type(
            str(args.component_library_type)
        ),
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

    if bool(getattr(args, "print_attribute_facets", False)):
        # Best-effort: shape inferred from frontend usage. If this fails, we document the failure.
        try:
            st2, facets = _post(
                url=FILTER_ATTRIBUTES_URL,
                payload=payload,
                timeout=float(args.timeout),
                use_json=bool(args.use_json),
            )
            _summarize_response("filterComponentAttribute", st2, facets)
        except Exception as exc:
            print(f"\n== filterComponentAttribute ==\nError: {exc}")

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
