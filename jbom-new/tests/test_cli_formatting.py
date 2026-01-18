import io
import unittest
from contextlib import redirect_stdout

from jbom.cli.formatting import Column, print_table


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
        # header, separator, then multiple wrapped lines
        data_lines = lines[2:]
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


if __name__ == "__main__":
    unittest.main()
