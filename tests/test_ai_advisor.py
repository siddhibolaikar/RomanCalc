import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from main import compile_source
from ai_advisor import explain_error
from errors import CompilerError


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)     # force the built-in rules


def error_for(text):
    stages, asm = compile_source(text)
    assert asm is None                                          # a failed compile has no assembly
    return stages


@pytest.mark.parametrize("text,must_contain", [
    ("IIII + I", "IV"),
    ("VX - II", "not allowed"),
    ("VV", "never be repeated"),
    ("MMMM", "3999"),
    ("XII + 5", "not allowed"),
    ("(X + V", "closed"),
    ("X V", "operator"),
    ("X + V)", "without a matching"),
    ("X /", "number"),
    ("X / (II - II)", "zero"),
    ("II - X", "negative"),
    ("MMMCMXCIX * MMMCMXCIX", "65535"),
])
def test_error_explanations(text, must_contain):
    stages = error_for(text)
    explanation = [s for s in stages if s[0].startswith("AI EXPLANATION")][0]
    assert explanation[0] == "AI EXPLANATION (built-in rules)"
    assert must_contain in explanation[2][0]


def test_explain_error_returns_text_and_source():
    text, who = explain_error(CompilerError("lexical", "bad", 0, "IIII"), "IIII")
    assert "IV" in text and who == "built-in rules"


def test_compiler_phases_never_import_the_ai_explainer():
    src = os.path.join(os.path.dirname(__file__), "..", "src")
    for name in ["lexer", "parser", "semantic", "codegen", "optimizer"]:
        text = open(os.path.join(src, name + ".py")).read()
        assert not re.search(r"^\s*(import|from)\s+ai_advisor", text, re.M), name
