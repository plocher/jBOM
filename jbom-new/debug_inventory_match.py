#!/usr/bin/env python3
"""Debug script to trace inventory matching logic for LED component."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from jbom.services.inventory_matcher import InventoryMatcher  # noqa: E402
from jbom.services.bom_generator import BOMEntry  # noqa: E402
from jbom.common.types import InventoryItem  # noqa: E402

# Create LED component as it appears in the BOM
led_entry = BOMEntry(
    references=["LED1"],
    value="RED",
    footprint="LED_0603",
    lib_id="Device:LED",
    quantity=1,
    attributes={},
)

# Create LED inventory item as it appears in the test
led_inventory = InventoryItem(
    ipn="LED-RED-0603-20mA",
    category="LED",
    value="RED",
    description="Red LED 20mA",
    package="0603",
    keywords="",
    type="",
    tolerance="",
    voltage="2V",
    amperage="",
    wattage="",
    lcsc="C2286",
    manufacturer="Kingbright",
    mfgpn="APT1608SRCPRV",
    datasheet="",
    smd="",
)

# Test the matching logic
matcher = InventoryMatcher()

print("=== LED Component Analysis ===")
print(f"Component: {led_entry.references[0]}")
print(f"Value: {led_entry.value}")
print(f"Footprint: {led_entry.footprint}")
print(f"LibID: {led_entry.lib_id}")

print("\n=== Package Extraction ===")
package = matcher._extract_package(led_entry.footprint)
print(f"Extracted Package: {package}")


print("\n=== Inventory Item ===")
print(f"IPN: {led_inventory.ipn}")
print(f"Value: {led_inventory.value}")
print(f"Package: {led_inventory.package}")
print(f"Description: {led_inventory.description}")

print("\n=== Inventory Items for Matching ===")
inventory_items = [led_inventory]
print(f"Available inventory items: {len(inventory_items)}")
for item in inventory_items:
    print(f"  {item.ipn}: value='{item.value}', package='{item.package}'")

print("\n=== Matching Logic ===")
print(f"Looking for component with value='{led_entry.value}' and package='{package}'")
print("\nTrying value-based matching:")
for item in inventory_items:
    if led_entry.value.upper() == item.value.upper():
        print(f"✓ Value match found: {item.ipn} ('{item.value}')")
        break
else:
    print("✗ No value-based match")

print("\n=== Final Match Test ===")
match = matcher._find_matching_inventory_item(led_entry, inventory_items)
if match:
    print(f"✓ Final match found: {match.ipn} - {match.description}")
else:
    print("✗ No final match found")
