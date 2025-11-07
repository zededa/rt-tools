import io
import re
import csv
from datetime import datetime
import pytest

from .test_output_parser import (
    MegabenchParser,
    build_caterpillar_parser,
    build_cyclictest_parser,
)


@pytest.fixture
def mock_files():
    """Return in-memory file-like objects for each test output."""
    return {
        "caterpillar_cat": io.StringIO(),
        "caterpillar_no_cat": io.StringIO(),
        "cyclictest_cat": io.StringIO(),
        "cyclictest_no_cat": io.StringIO(),
    }


@pytest.fixture
def parser(mock_files):
    """Create a MegabenchParser with in-memory file objects."""
    return MegabenchParser(
        caterpillar_cat=mock_files["caterpillar_cat"],
        caterpillar_no_cat=mock_files["caterpillar_no_cat"],
        cyclictest_cat=mock_files["cyclictest_cat"],
        cyclictest_no_cat=mock_files["cyclictest_no_cat"],
    )


def test_caterpillar_section_parsing(parser, mock_files):
    """Test parsing a Caterpillar without CAT section."""
    start = "Benchmarking Caterpillar without CAT..."
    end = "Caterpillar without CAT benchmark complete"
    line = "   1    2    3    4    5    6    7   "

    # Simulate log flow
    parser.parse(start)
    parser.parse(line)
    parser.parse(end)

    output = mock_files["caterpillar_no_cat"].getvalue().strip().splitlines()

    # Expect header + 1 parsed line
    assert len(output) == 2
    assert output[0].startswith("timestamp,SampleMin,SampleMax,SmplJitter")
    assert re.match(r"^\d{4}-\d{2}-\d{2}", output[1])  # timestamp present
    assert ",1,2,3,4,5,6,7" in output[1]


def test_cyclictest_section_parsing(parser, mock_files):
    """Test parsing a CyclicTest with CAT section."""
    start = "Benchmarking CyclicTest with CAT..."
    end = "CyclicTest with CAT benchmark complete"
    line = "T: 1 ( 2 ) P: 3 I: 4 C: 5 Min: 6 Act: 7 Avg: 8 Max: 9"

    parser.parse(start)
    parser.parse(line)
    parser.parse(end)

    output = mock_files["cyclictest_cat"].getvalue().strip().splitlines()

    assert len(output) == 2
    assert output[0].startswith("timestamp,T,T_ID,P,I,C,Min,Act,Avg,Max")
    assert ",1,2,3,4,5,6,7,8,9" in output[1]


def test_ignores_lines_outside_sections(parser, mock_files):
    """Lines outside sections should not write anything."""
    parser.parse("some random output line")
    for f in mock_files.values():
        assert f.getvalue() == ""


def test_switching_between_sections(parser, mock_files):
    """Ensure it resets correctly when moving between tests."""
    cat_start = "Benchmarking Caterpillar with CAT..."
    cat_end = "Caterpillar with CAT benchmark complete"
    cyc_start = "Benchmarking CyclicTest without CAT..."
    cyc_end = "CyclicTest without CAT benchmark complete"

    cat_line = "   11   12   13   14   15   16   17"
    cyc_line = "T: 10 ( 11 ) P: 12 I: 13 C: 14 Min: 15 Act: 16 Avg: 17 Max: 18"

    parser.parse(cat_start)
    parser.parse(cat_line)
    parser.parse(cat_end)
    parser.parse(cyc_start)
    parser.parse(cyc_line)
    parser.parse(cyc_end)

    cat_output = mock_files["caterpillar_cat"].getvalue().strip().splitlines()
    cyc_output = mock_files["cyclictest_no_cat"].getvalue().strip().splitlines()

    # Each file should have header + one parsed line
    assert len(cat_output) == 2
    assert len(cyc_output) == 2


def test_non_matching_line_inside_section(parser, mock_files):
    """Non-matching lines inside a section should be ignored."""
    start = "Benchmarking Caterpillar without CAT..."
    end = "Caterpillar without CAT benchmark complete"
    parser.parse(start)
    parser.parse("this line won't match regex")
    parser.parse(end)

    output = mock_files["caterpillar_no_cat"].getvalue().strip().splitlines()

    # Only header should be written, no parsed data
    assert len(output) == 1
    assert output[0].startswith("timestamp,SampleMin")
