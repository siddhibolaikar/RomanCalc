import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from pipeline import run_pipeline
from ai_advisor import explain_error


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)   # force offline fallback


@pytest.mark.parametrize("src,must_contain", [
    ("IIII + I", "IV"),
    ("VX - II", "subtractive"),
    ("VV", "never be repeated"),
    ("XII + 5", "not allowed"),
    ("(X + V", "closed"),
    ("X V", "operator"),
    ("X / (II - II)", "zero"),
])
def test_offline_error_explanations(src, must_contain):
    err = run_pipeline(src)["error"]
    out = explain_error(err, src)
    assert out["source"] == "offline" and must_contain in out["text"]


def test_core_compiler_never_imports_ai_layer():
    # The AI layer must stay advisory: no compiler module may depend on it.
    src_dir = os.path.join(os.path.dirname(__file__), "..", "src")
    for name in ["lexer", "parser", "semantic", "codegen", "optimizer", "pipeline", "ops"]:
        text = open(os.path.join(src_dir, name + ".py")).read()
        assert not re.search(r"^\s*(import|from)\s+ai_advisor", text, re.M), name
