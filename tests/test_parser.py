import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser, tree_to_str, tree_lines
from errors import CompilerError


def parse(text):
    return Parser(tokenize(text)).parse()


def test_multiplication_binds_tighter():
    assert tree_to_str(parse("XII + IV * II")) == "(XII + (IV * II))"


def test_brackets_change_the_grouping():
    assert tree_to_str(parse("(XII + IV) * II")) == "((XII + IV) * II)"


def test_subtraction_goes_left_to_right():
    assert tree_to_str(parse("X - V - II")) == "((X - V) - II)"


def test_tree_lines_one_node_per_line():
    assert tree_lines(parse("XII + IV")) == ["+", "    XII", "    IV"]


@pytest.mark.parametrize("text", ["XII +", "+ XII", "(XII + IV", "()", "XII IV", "* XII", "XII + IV)", ""])
def test_syntax_errors(text):
    with pytest.raises(CompilerError) as e:
        parse(text)
    assert e.value.phase == "syntax"
