import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser, tree_to_str
from errors import CompilerError


def parse(src):
    return Parser(tokenize(src)).parse()


def test_precedence_multiplication_binds_tighter():
    tree = parse("XII + IV * II")
    assert tree_to_str(tree) == "(XII + (IV * II))"


def test_parentheses_override_precedence():
    tree = parse("(XII + IV) * II")
    assert tree_to_str(tree) == "((XII + IV) * II)"


def test_left_associativity():
    tree = parse("X - V - II")
    assert tree_to_str(tree) == "((X - V) - II)"


@pytest.mark.parametrize("src", [
    "XII +",       # trailing operator
    "+ XII",       # leading operator
    "(XII + IV",   # unbalanced parens
    "()",          # empty parens
    "XII IV",      # missing operator between numerals
    "* XII",       # operator with no left operand
])
def test_syntax_errors(src):
    with pytest.raises(CompilerError) as exc:
        parse(src)
    assert exc.value.phase == "syntax"
