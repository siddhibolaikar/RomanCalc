import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
import ai_advisor
from ai_advisor import suggest_fixes, rule_fix
from main import compile_source, run_phases


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)     # no AI: only the built-in rules


def error_of(text):
    _, _, error = run_phases(text)
    return error


def titles(stages):
    return [s[0] for s in stages]


# ---------------- the built-in fix rules ----------------
@pytest.mark.parametrize("text,fixed", [
    ("IIII + I", "IV + I"), ("VV * II", "X * II"), ("IXIX", "XVIII"), ("X + IC", "X + XCIX"),
    ("(X + V", "(X + V)"), ("((X + V) * II", "((X + V) * II)"), ("(X + (V * II", "(X + (V * II))"),
    ("X + V)", "X + V"), ("VX - II", "V - II"), ("iiii", "IV"),
])
def test_rule_fix(text, fixed):
    assert rule_fix(error_of(text), text) == fixed


@pytest.mark.parametrize("text", ["MMMM", "XII +", "X / (II - II)", "XII IV", "(X V)", "X + 5", "II - X"])
def test_no_rule_fix_for_unclear_mistakes(text):
    assert rule_fix(error_of(text), text) is None


# ---------------- the compiler verifies the fix ----------------
def test_fix_is_verified_by_the_compiler():
    stages, asm = compile_source("IIII + I")
    assert asm is None                                          # the original input is still an error
    assert titles(stages)[-2:] == ["SUGGESTED FIX (built-in rules)", "VERIFIED: ALL 5 PHASES PASSED"]
    assert stages[-2][2] == ["IIII + I   ->   IV + I"]
    _, fixed_asm = compile_source("IV + I")
    assert stages[-1][2] == fixed_asm == ["LXI SP, 0FFFFH", "LXI H, 0005H", "HLT"]


@pytest.mark.parametrize("text", ["XII +", "X / (II - II)", "II - X", "MMMM", "XII IV"])
def test_no_fix_when_nothing_passes_the_compiler(text):
    stages, asm = compile_source(text)
    assert asm is None and titles(stages)[-1] == "NO VERIFIED FIX"


def test_valid_input_has_no_fix_stages():
    stages, asm = compile_source("XII + IV")
    assert asm is not None and not any("FIX" in t for t in titles(stages))


# ---------------- AI proposes, compiler decides ----------------
def test_a_bad_ai_suggestion_is_rejected_then_the_rules_are_tried(monkeypatch):
    monkeypatch.setattr(ai_advisor, "ask_ai_for_fix", lambda error, source: "XII ++")
    stages, _ = compile_source("IIII + I")
    assert titles(stages)[-2] == "SUGGESTED FIX (built-in rules)"
    rejected = stages[-2][2][0]
    assert rejected.startswith("AI suggested 'XII ++', but the compiler rejected it")
    assert stages[-2][2][1] == "IIII + I   ->   IV + I"


def test_a_good_ai_suggestion_is_accepted(monkeypatch):
    monkeypatch.setattr(ai_advisor, "ask_ai_for_fix", lambda error, source: "IV + I")
    stages, _ = compile_source("IIII + I")
    assert titles(stages)[-2:] == ["SUGGESTED FIX (AI)", "VERIFIED: ALL 5 PHASES PASSED"]


def test_ai_suggestion_that_still_fails_gives_no_fix(monkeypatch):
    monkeypatch.setattr(ai_advisor, "ask_ai_for_fix", lambda error, source: "X / (V - V)")
    stages, _ = compile_source("X / (II - II)")
    assert titles(stages)[-1] == "NO VERIFIED FIX"
    assert "division by zero" in stages[-1][2][0]


def test_suggest_fixes_skips_unchanged_and_duplicate_suggestions(monkeypatch):
    error = error_of("IIII + I")
    monkeypatch.setattr(ai_advisor, "ask_ai_for_fix", lambda e, s: "IIII + I")       # same as the input
    assert suggest_fixes(error, "IIII + I") == [("IV + I", "built-in rules")]
    monkeypatch.setattr(ai_advisor, "ask_ai_for_fix", lambda e, s: "IV + I")         # same as the rule's fix
    assert suggest_fixes(error, "IIII + I") == [("IV + I", "AI")]


def test_only_the_first_line_of_the_ai_answer_is_used(monkeypatch):
    monkeypatch.setattr(ai_advisor, "call_ai", lambda question, max_tokens: "`IV + I`\nBecause IIII is wrong.")
    assert ai_advisor.ask_ai_for_fix(error_of("IIII + I"), "IIII + I") == "IV + I"
