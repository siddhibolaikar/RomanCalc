import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize, roman_to_int, int_to_roman
from errors import CompilerError


@pytest.mark.parametrize("s,expected", [
    ("I", 1), ("III", 3), ("IV", 4), ("IX", 9),
    ("XII", 12), ("XL", 40), ("XC", 90),
    ("MCMXCIX", 1999), ("MMMCMXCIX", 3999),
    ("MCDXLIV", 1444),
])
def test_valid_numerals(s, expected):
    tokens = tokenize(s)
    assert tokens[0].value == expected


@pytest.mark.parametrize("s", ["IIII", "VX", "IC", "XXXX", "VV", "LL", "IXIX", "MMMM"])
def test_invalid_numerals(s):
    with pytest.raises(CompilerError) as exc:
        tokenize(s)
    assert exc.value.phase == "lexical"


def test_operators_and_parens():
    tokens = tokenize("XII + ( IV * II )")
    types = [t.type for t in tokens]
    assert types == [
        "ROMAN_NUM", "PLUS", "LPAREN", "ROMAN_NUM", "STAR", "ROMAN_NUM", "RPAREN", "EOF"
    ]


def test_unexpected_character():
    with pytest.raises(CompilerError) as exc:
        tokenize("XII + 5")
    assert exc.value.phase == "lexical"


def test_round_trip_all_values():
    for i in range(1, 4000):
        assert roman_to_int(int_to_roman(i)) == i
