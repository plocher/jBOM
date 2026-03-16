import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from jbom.cli.formatting import (
    Column,
    print_inventory_table,
    print_table,
    print_tabular_data,
)


class TestConsoleFormatting(unittest.TestCase):
    def render(self, rows, columns, width=None, title=None):
        buf = io.StringIO()
        with redirect_stdout(buf):
            print_table(rows, columns, terminal_width=width, title=title)
        return buf.getvalue().splitlines()

    def test_separator_matches_header_length(self):
        cols = [
            Column("A", "a", preferred_width=5),
            Column("B", "b", preferred_width=5),
            Column("C", "c", preferred_width=5),
        ]
        rows = [{"a": "one", "b": "two", "c": "three"}]
        lines = self.render(rows, cols, width=80)
        header = lines[0]
        separator = lines[1]
        self.assertEqual(len(header), len(separator))
        # Ensure separator is composed of dashes and +- at column boundaries
        self.assertIn("-+-", separator)
        self.assertTrue(all(ch in "-+" for ch in set(separator)))

    def test_wrapping_aligns_columns(self):
        cols = [
            Column("Ref", "ref", wrap=True, preferred_width=6),
            Column("Footprint", "fp", wrap=True, preferred_width=10),
        ]
        rows = [
            {
                "ref": "R1 R2 R3 R4",  # wraps in first column
                "fp": "VeryLongFootprintName That Wraps",
            }
        ]
        lines = self.render(rows, cols, width=25)
        # header, separator, then at least two data lines
        self.assertGreaterEqual(len(lines), 4)
        header = lines[0]
        sep = lines[1]
        data1 = lines[2]
        data2 = lines[3]
        # Find separator positions from header
        split_pos = header.find(" | ")
        self.assertGreater(split_pos, 0)
        # Verify each data line has separator at same index
        self.assertEqual(data1.find(" | "), split_pos)
        self.assertEqual(data2.find(" | "), split_pos)
        # Separator length equals header length
        self.assertEqual(len(header), len(sep))

    def test_fixed_numeric_columns_preserved_when_shrinking(self):
        cols = [
            Column(
                "Reference",
                "ref",
                wrap=True,
                preferred_width=20,
                fixed=False,
                align="left",
            ),
            Column("X", "x", wrap=False, preferred_width=8, fixed=True, align="right"),
            Column("Y", "y", wrap=False, preferred_width=7, fixed=True, align="right"),
        ]
        rows = [
            {"ref": "U1 Very Long Reference That Wraps", "x": "123.4567", "y": "9.0000"}
        ]
        # Constrain width to force shrinking
        lines = self.render(rows, cols, width=24)
        # Ensure numeric columns remain right-aligned
        data = lines[2]
        parts = data.split(" | ")
        self.assertEqual(len(parts), 3)
        # X and Y should be right-aligned (no trailing spaces)
        self.assertTrue(parts[1].endswith("4567"))
        self.assertTrue(parts[2].endswith("0000"))

    def test_mixed_alignment(self):
        cols = [
            Column("Left", "l", wrap=False, preferred_width=6, align="left"),
            Column("Right", "r", wrap=False, preferred_width=6, align="right"),
        ]
        rows = [{"l": "ab", "r": "12"}]
        lines = self.render(rows, cols, width=20)
        data = lines[2]
        parts = data.split(" | ")
        self.assertEqual(parts[0], "ab".ljust(len(parts[0])))
        self.assertTrue(parts[1].endswith("12"))
        self.assertEqual(parts[1].strip(), "12")

    def test_unbreakable_string_wrapping(self):
        cols = [Column("Blob", "b", wrap=True, preferred_width=8)]
        long = "X" * 25
        rows = [{"b": long}]
        lines = self.render(rows, cols, width=10)
        # header, separator, then multiple wrapped lines, then a row separator
        # Filter out the row separator (contains only dashes/plus)
        data_lines = [line for line in lines[2:] if not all(c in "-+" for c in line)]
        # Expect 4 wrapped lines for 25 chars with width ~8
        self.assertEqual(len(data_lines), 4)
        # Ensure no line exceeds a reasonable bound (terminal width 10 here)
        self.assertLessEqual(max(len(dl) for dl in data_lines), 10)
        # Combined content (without spaces) equals original
        content = "".join(dl.strip() for dl in data_lines)
        self.assertEqual(content, long)

    def test_missing_keys_render_as_blank(self):
        cols = [
            Column("A", "a", wrap=False, preferred_width=5),
            Column("B", "b", wrap=False, preferred_width=5),
        ]
        rows = [{"a": "x"}]  # missing 'b'
        lines = self.render(rows, cols, width=80)
        parts = lines[2].split(" | ")
        self.assertEqual(parts[0].strip(), "x")
        self.assertEqual(parts[1].strip(), "")

    def test_title_underline_length(self):
        cols = [Column("A", "a", preferred_width=5)]
        rows = [{"a": "val"}]
        title = "This is a long title"
        lines = self.render(rows, cols, width=15, title=title)
        header = lines[2]
        underline = lines[1]
        expected_len = min(len(title), max(20, len(header)))
        self.assertEqual(len(underline), expected_len)

    def test_print_tabular_data_with_transformer(self):
        """Test print_tabular_data with row transformation and sorting."""

        class TestData:
            def __init__(self, name, value):
                self.name = name
                self.value = value

        def transformer(item):
            return {"n": item.name, "v": str(item.value)}

        data = [TestData("C", 3), TestData("A", 1), TestData("B", 2)]
        cols = [Column("Name", "n"), Column("Value", "v")]

        buf = io.StringIO()
        with redirect_stdout(buf):
            print_tabular_data(
                data,
                cols,
                row_transformer=transformer,
                sort_key=lambda x: x.name,
                summary_line="Test summary",
            )
        lines = buf.getvalue().splitlines()

        # Should have blank line, header, separator, 3 data lines, blank line, summary
        self.assertGreaterEqual(len(lines), 7)
        # Check sorting - first data item should be A
        data_start_idx = next(i for i, line in enumerate(lines) if "A" in line)
        self.assertIn("A", lines[data_start_idx])
        # Check summary line at end
        self.assertEqual(lines[-1], "Test summary")

    def test_print_tabular_data_no_transformer(self):
        """Test print_tabular_data with raw dict data."""
        data = [{"name": "test", "val": "123"}]
        cols = [Column("Name", "name"), Column("Value", "val")]

        buf = io.StringIO()
        with redirect_stdout(buf):
            print_tabular_data(data, cols, title="Test Title")
        lines = buf.getvalue().splitlines()

        # Should have blank line, title, underline, header, separator, data, blank
        self.assertGreaterEqual(len(lines), 7)
        # Check title appears
        title_idx = next(i for i, line in enumerate(lines) if "Test Title" in line)
        self.assertEqual(lines[title_idx], "Test Title")

    def test_print_inventory_table_renders_all_fieldnames(self):
        """print_inventory_table must show every field in fieldnames, not a hardcoded subset."""
        fieldnames = [
            "Project",
            "UUID",
            "SourceFile",
            "Refs",
            "Category",
            "IPN",
            "Value",
        ]
        rows = [
            {
                "Project": "/some/path",
                "UUID": "uuid-r1",
                "SourceFile": "/some/path/top.kicad_sch",
                "Refs": "R1",
                "Category": "RES",
                "IPN": "",
                "Value": "10K",
            }
        ]
        buf = io.StringIO()
        # Use a wide terminal so no column shrinks below its header width.
        with patch("jbom.cli.formatting.get_terminal_width", return_value=400):
            with redirect_stdout(buf):
                print_inventory_table(rows, fieldnames)
        out = buf.getvalue()
        # Every field name must appear as a column header (no whitelist truncation).
        for field in fieldnames:
            self.assertIn(field, out, f"Column '{field}' missing from console output")
        # Data values must also be present.
        self.assertIn("uuid-r1", out)
        self.assertIn("RES", out)
        self.assertIn("10K", out)

    def test_row_separator_emitted_after_each_data_row(self):
        """A -+- row separator must appear after every data row."""
        cols = [
            Column("A", "a", preferred_width=5),
            Column("B", "b", preferred_width=5),
        ]
        rows = [{"a": "one", "b": "two"}, {"a": "foo", "b": "bar"}]
        lines = self.render(rows, cols, width=20)
        # header(0), header_sep(1), row1(2), row_sep(3), row2(4), row_sep(5)
        self.assertEqual(len(lines), 6)
        for sep_idx in (3, 5):
            self.assertIn("-+-", lines[sep_idx])
            self.assertTrue(all(c in "-+" for c in set(lines[sep_idx])))

    def test_explicit_newline_in_cell_renders_as_two_lines(self):
        """An explicit \\n in cell text must produce two separate visual lines."""
        cols = [Column("Field", "f", preferred_width=12, wrap=True)]
        rows = [{"f": "(Optional)\nIPN"}]
        lines = self.render(rows, cols, width=20)
        # header(0), sep(1), "(Optional)"(2), "IPN"(3), row_sep(4)
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[2].strip(), "(Optional)")
        self.assertEqual(lines[3].strip(), "IPN")
        # Row separator contains only dashes
        self.assertTrue(all(c in "-+" for c in set(lines[4])))

    def test_explicit_newline_in_non_wrapping_column_is_bounded(self):
        """Explicit \\n in a non-wrapping column should still render bounded multiline output."""
        cols = [
            Column("A", "a", preferred_width=8, wrap=False),
            Column("B", "b", preferred_width=8, wrap=False),
        ]
        rows = [{"a": "X", "b": "MISSING\n(620-750nm)"}]
        lines = self.render(rows, cols, width=24)
        data_lines = [line for line in lines[2:] if " | " in line]
        self.assertGreaterEqual(len(data_lines), 2)
        for line in data_lines:
            self.assertEqual(line.find(" | "), lines[0].find(" | "))
        self.assertTrue(any("MISSING" in line for line in data_lines))
        self.assertTrue(any("(620-" in line for line in data_lines))

    def test_delimiter_wrap_prefers_colon_over_hard_split(self):
        """Delimiter-aware wrapping should split at ':' before hard truncation."""
        cols = [Column("Field", "f", preferred_width=15, wrap=True)]
        rows = [{"f": "SPCoast:0603-LED"}]
        lines = self.render(rows, cols, width=15)
        # header(0), sep(1), first wrapped line(2), second wrapped line(3), row_sep(4)
        self.assertEqual(lines[2].strip(), "SPCoast:")
        self.assertEqual(lines[3].strip(), "0603-LED")

    def test_delimiter_wrap_supports_underscore_and_hyphen(self):
        """Delimiter-aware wrapping should split long unspaced tokens on '_' and '-'."""
        cols = [Column("Field", "f", preferred_width=10, wrap=True)]
        rows = [{"f": "Library_Name-Variant"}]
        lines = self.render(rows, cols, width=10)
        wrapped_lines = [line.strip() for line in lines[2:5]]
        self.assertEqual(wrapped_lines, ["Library_", "Name-", "Variant"])

    def test_delimiter_wrap_supports_slash_for_paths(self):
        """Delimiter-aware wrapping should split path-like values on '/'."""
        cols = [Column("Path", "p", preferred_width=12, wrap=True)]
        rows = [{"p": "/Users/jplocher/Dropbox/KiCad/projects"}]
        lines = self.render(rows, cols, width=12)
        wrapped_lines = [
            line.strip()
            for line in lines[2:]
            if line.strip() and not all(char in "-+" for char in line.strip())
        ]
        self.assertEqual(
            wrapped_lines,
            ["/Users/", "jplocher/", "Dropbox/", "KiCad/", "projects"],
        )

    def test_delimiter_at_exact_boundary_does_not_overflow_column(self):
        """Preferred delimiter at width boundary must not create over-width chunks."""
        cols = [Column("Field", "f", preferred_width=10, wrap=True)]
        rows = [{"f": "1234567890-abc"}]
        lines = self.render(rows, cols, width=10)
        wrapped_lines = [line.strip() for line in lines[2:4]]
        self.assertEqual(wrapped_lines, ["1234567890", "-abc"])


if __name__ == "__main__":
    unittest.main()
