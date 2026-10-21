import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize, roman_to_int, int_to_roman
from errors import CompilerError


@pytest.mark.parametrize("text,value", [
    ("I", 1), ("III", 3), ("IV", 4), ("IX", 9), ("XII", 12), ("XL", 40),
    ("XC", 90), ("MCMXCIX", 1999), ("MMMCMXCIX", 3999), ("MCDXLIV", 1444),
])
def test_valid_numerals(text, value):
    assert tokenize(text)[0].value == value


@pytest.mark.parametrize("text", ["IIII", "VX", "IC", "XXXX", "VV", "LL", "IXIX", "MMMM"])
def test_invalid_numerals(text):
    with pytest.raises(CompilerError) as e:
        tokenize(text)
    assert e.value.phase == "lexical"


def test_token_types():
    types = [t.type for t in tokenize("XII + ( IV * II )")]
    assert types == ["NUM", "+", "(", "NUM", "*", "NUM", ")", "END"]


def test_lowercase_is_accepted():
    assert tokenize("xii")[0].lexeme == "XII"


def test_unexpected_character():
    with pytest.raises(CompilerError) as e:
        tokenize("XII + 5")
    assert e.value.phase == "lexical" and e.value.lexeme == "5"


def test_round_trip_all_values():
    for n in range(1, 4000):
        assert roman_to_int(int_to_roman(n)) == n
