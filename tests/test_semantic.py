import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser
from semantic import analyze, check_representable
from errors import CompilerError


def evaluate(src):
    tree = Parser(tokenize(src)).parse()
    return analyze(tree)


@pytest.mark.parametrize("src,expected", [
    ("XII + IV * II", 20),
    ("(XII + IV) * II", 32),
    ("X / II", 5),
    ("X - V - II", 3),
    ("III * III * III", 27),
])
def test_evaluation(src, expected):
    assert evaluate(src) == expected


def test_division_by_zero():
    with pytest.raises(CompilerError) as exc:
        evaluate("X / (II - II)")
    assert exc.value.phase == "semantic"


def test_representable_check():
    with pytest.raises(CompilerError):
        check_representable(5000)
    check_representable(3999)  # should not raise
    check_representable(1)     # should not raise
