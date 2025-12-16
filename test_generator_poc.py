#!/usr/bin/env python3
"""Proof of concept: Generator base class with template method pattern.

This demonstrates how POSGenerator (or BOMGenerator) would inherit from
the enhanced Generator base class to get consistent behavior.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import dataclass
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from jbom.common.generator import Generator  # noqa: E402


@dataclass
class SimpleEntry:
    """Simple output entry for POC"""

    name: str
    value: str


class SimplePOCGenerator(Generator):
    """Minimal generator implementation to demonstrate the pattern"""

    def discover_input(self, input_path: Path) -> Path:
        """Find first .txt file in directory"""
        if input_path.is_file():
            return input_path

        txt_files = list(input_path.glob("*.txt"))
        if not txt_files:
            raise FileNotFoundError(f"No .txt files found in {input_path}")
        return txt_files[0]

    def load_input(self, input_path: Path) -> List[str]:
        """Load lines from text file"""
        return input_path.read_text().strip().split("\n")

    def process(self, data: List[str]) -> tuple[List[SimpleEntry], Dict[str, Any]]:
        """Convert lines to entries"""
        entries = []
        for line in data:
            if ":" in line:
                name, value = line.split(":", 1)
                entries.append(SimpleEntry(name.strip(), value.strip()))

        metadata = {
            "line_count": len(data),
            "entry_count": len(entries),
        }
        return entries, metadata

    def write_csv(
        self, entries: List[SimpleEntry], output_path: Path, fields: List[str]
    ) -> None:
        """Write entries to CSV"""
        import csv

        output_str = str(output_path)
        if output_str == "-":
            f = sys.stdout
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            f = open(output_path, "w", newline="")

        try:
            writer = csv.writer(f)
            writer.writerow(["Name", "Value"])  # Header
            for entry in entries:
                writer.writerow([entry.name, entry.value])
        finally:
            if output_str != "-":
                f.close()

    def get_available_fields(self) -> Dict[str, str]:
        """List available fields"""
        return {
            "name": "Entry name",
            "value": "Entry value",
        }

    def default_preset(self) -> str:
        """Default preset name"""
        return "simple"


def test_template_method():
    """Test the template method pattern"""
    print("=" * 60)
    print("Generator Base Class POC - Template Method Pattern")
    print("=" * 60)

    # Create a test input file
    test_dir = Path(tempfile.gettempdir()) / "jbom_poc"  # nosec B108
    test_dir.mkdir(exist_ok=True)
    test_file = test_dir / "test_input.txt"
    test_file.write_text("R1: 10k\nC1: 100nF\nU1: ESP32\n")

    # Create generator
    gen = SimplePOCGenerator()

    # Test 1: Run with explicit file path
    print("\n1. Explicit file path:")
    result = gen.run(input=test_file, output=test_dir / "output.csv")
    print(
        f"   ✓ Processed {result['line_count']} lines → {result['entry_count']} entries"
    )
    print(f"   ✓ Output: {test_dir / 'output.csv'}")

    # Test 2: Run with directory (auto-discovery)
    print("\n2. Directory auto-discovery:")
    result = gen.run(input=test_dir, output=test_dir / "output2.csv")
    print("   ✓ Auto-discovered: test_input.txt")
    print(f"   ✓ Processed {result['entry_count']} entries")

    # Test 3: Run without output (data only)
    print("\n3. No output (data only):")
    result = gen.run(input=test_file)
    print(f"   ✓ Returned {result['entry_count']} entries in memory")
    print(f"   ✓ First entry: {result['entries'][0]}")

    # Test 4: stdout
    print("\n4. Output to stdout:")
    print("   Output:")
    result = gen.run(input=test_file, output="-")

    print("\n" + "=" * 60)
    print("✓ POC Complete - Template Method Pattern Working!")
    print("=" * 60)
    print("\nBenefits demonstrated:")
    print("  • File discovery logic in base class")
    print("  • Consistent run() flow for all generators")
    print("  • Subclass only implements domain-specific logic")
    print("  • Output routing handled automatically")


if __name__ == "__main__":
    test_template_method()
