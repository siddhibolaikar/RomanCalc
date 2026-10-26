import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser
from semantic import analyze, calculate
from errors import CompilerError


def value_of(text):
    return analyze(Parser(tokenize(text)).parse())


@pytest.mark.parametrize("text,expected", [
    ("XII + IV * II", 20), ("(XII + IV) * II", 32), ("X / II", 5),
    ("X - V - II", 3), ("III * III * III", 27), ("X - X", 0), ("X / III", 3), ("MMMCMXCIX * XVI", 63984),
])
def test_values(text, expected):
    assert value_of(text) == expected


def test_every_node_gets_a_val():
    tree = Parser(tokenize("XII + IV * II")).parse()
    analyze(tree)
    assert (tree.val, tree.left.val, tree.right.val) == (20, 12, 8)


def test_division_by_zero():
    with pytest.raises(CompilerError) as e:
        value_of("X / (II - II)")
    assert e.value.phase == "semantic"


def test_calculate():
    assert calculate("+", 2, 3) == 5 and calculate("*", 2, 3) == 6 and calculate("/", 7, 2) == 3


@pytest.mark.parametrize("text", ["II - X", "MMMCMXCIX * MMMCMXCIX", "MMMCMXCIX * XVII"])
def test_value_must_fit_in_16_bits(text):
    with pytest.raises(CompilerError) as e:
        value_of(text)
    assert e.value.phase == "semantic" and "16 bits" in e.value.message
