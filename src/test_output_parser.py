from abc import ABC, abstractmethod
from typing import Generator, IO, Sequence, Optional, TextIO
from datetime import datetime
from pathlib import Path

import io
import csv
import re


class RegexParser:
    """
    Parses text lines with a regex and produces CSV-formatted output.
    """

    def __init__(self, pattern: str, headers: Sequence[str]):
        """
        :param pattern: Regex pattern with capture groups
        :param headers: Column names for CSV header
        """
        self.regex = re.compile(pattern)
        self.headers = headers

    def prelude(self) -> Optional[str]:
        """
        Returns the CSV header as a string, or None if no headers are defined.
        """
        if not self.headers:
            return None

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["timestamp"] + list(self.headers))
        return buffer.getvalue()

    def parse(self, line: str) -> Optional[str]:
        """
        Parses a single line of text and returns a CSV-formatted string
        if it matches the regex, otherwise returns None.
        """
        line = line.strip()
        if not line:
            return None

        match = self.regex.search(line)
        if not match:
            return None

        values = [match.group(i + 1) for i in range(len(self.headers))]
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = [current_time] + values

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(values)
        return buffer.getvalue()


def build_cyclictest_parser() -> RegexParser:
    cyclictest_pattern = (
        r"T:\s*(\d+)\s*\(\s*(\d+)\s*\)\s*"
        r"P:\s*(\d+)\s*I:\s*(\d+)\s*C:\s*(\d+)\s*"
        r"Min:\s*(\d+)\s*Act:\s*(\d+)\s*Avg:\s*(\d+)\s*Max:\s*(\d+)"
    )
    cyclictest_headers = ["T", "T_ID", "P", "I", "C", "Min", "Act", "Avg", "Max"]
    return RegexParser(
        pattern=cyclictest_pattern,
        headers=cyclictest_headers,
    )


def build_caterpillar_parser() -> RegexParser:
    caterpillar_headers = [
        "SampleMin",
        "SampleMax",
        "SmplJitter",
        "SessionMin",
        "SessionMax",
        "SessionJitter",
        "Sample",
    ]

    caterpillar_pattern = (
        r"^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$"
    )

    return RegexParser(
        pattern=caterpillar_pattern,
        headers=caterpillar_headers,
    )


class MegabenchParser:
    """
    Parses output of a 48-hours benchmark, which consists of 4 tests:
     1) caterpillar without CAT
     2) caterpillar with CAT
     3) cyclictest without CAT
     4) cyclictest with CAT

    Each test is between specific lines
    """

    def __init__(
        self,
        caterpillar_cat: TextIO,
        caterpillar_no_cat: TextIO,
        cyclictest_cat: TextIO,
        cyclictest_no_cat: TextIO,
    ):
        self.cyclictest_parser = build_cyclictest_parser()
        self.caterpillar_parser = build_caterpillar_parser()

        self.indicators = {
            "Benchmarking Caterpillar without CAT...": {
                "end": "Caterpillar without CAT benchmark complete",
                "parser": self.caterpillar_parser,
                "file": caterpillar_no_cat,
            },
            "Benchmarking Caterpillar with CAT...": {
                "end": "Caterpillar with CAT benchmark complete",
                "parser": self.caterpillar_parser,
                "file": caterpillar_cat,
            },
            "Benchmarking CyclicTest without CAT...": {
                "end": "CyclicTest without CAT benchmark complete",
                "parser": self.cyclictest_parser,
                "file": cyclictest_no_cat,
            },
            "Benchmarking CyclicTest with CAT...": {
                "end": "CyclicTest with CAT benchmark complete",
                "parser": self.cyclictest_parser,
                "file": cyclictest_cat,
            },
        }
        self.current_test = None

    def parse(self, line: str):
        if self.current_test is None:
            for start, test in self.indicators.items():
                if start in line:
                    self.current_test = start
                    test["file"].write(test["parser"].prelude())
        else:
            test = self.indicators[self.current_test]
            if test["end"] in line:
                self.current_test = None
            else:
                parsed = test["parser"].parse(line)
                if parsed is not None:
                    test["file"].write(parsed)
