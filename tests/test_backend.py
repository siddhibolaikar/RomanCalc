import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser
from semantic import analyze
from codegen import generate_code, VM, fmt
from optimizer import optimize
from pipeline import run_pipeline, to_roman, PHASE_INFO
from errors import CompilerError


def checked_tree(src):
    tree = Parser(tokenize(src)).parse()
    analyze(tree)
    return tree


def program(src):
    return [fmt(i) for i in generate_code(checked_tree(src))]


# ---------------- code generation ----------------
def test_codegen_respects_precedence():
    assert program("XII + IV * II") == ["PUSH 12", "PUSH 4", "PUSH 2", "MUL", "ADD", "PRINT", "HALT"]


def test_codegen_parentheses():
    assert program("(XII + IV) * II") == ["PUSH 12", "PUSH 4", "ADD", "PUSH 2", "MUL", "PRINT", "HALT"]


def test_codegen_single_numeral():
    assert program("XII") == ["PUSH 12", "PRINT", "HALT"]


# ---------------- optimization (constant folding) ----------------
def test_optimizer_folds_chain_to_one_push():
    code = generate_code(checked_tree("XII + IV * II"))
    opt, log = optimize(code)
    assert [fmt(i) for i in opt] == ["PUSH 20", "PRINT", "HALT"]
    assert len(log) == 2 and "PUSH 8" in log[0]


def test_optimizer_leaves_already_minimal_code_alone():
    code = generate_code(checked_tree("XII"))
    opt, log = optimize(code)
    assert opt == code and log == []


def test_optimizer_is_shorter():
    code = generate_code(checked_tree("(XII + IV) * II - X / V"))
    opt, _ = optimize(code)
    assert len(opt) < len(code)


@pytest.mark.parametrize("src", ["XII + IV * II", "(XII + IV) * II - X / V", "XII", "M - I - I", "X - XX"])
def test_vm_matches_semantic_before_and_after_optimization(src):
    tree = Parser(tokenize(src)).parse()
    value = analyze(tree)
    code = generate_code(tree)
    opt, _ = optimize(code)
    assert VM().run(code)["output"] == value
    assert VM().run(opt)["output"] == value


def test_vm_runtime_errors():
    with pytest.raises(CompilerError):
        VM().run([("ADD",)])                       # stack underflow
    with pytest.raises(CompilerError):
        VM().run([("PUSH", 1), ("PUSH", 0), ("DIV",)])


# ---------------- pipeline ----------------
def test_to_roman():
    assert to_roman(20) == ("XX", "")
    assert to_roman(0)[0] is None and to_roman(-3)[0] is None and to_roman(7998)[0] is None


def test_pipeline_success():
    r = run_pipeline("XII + IV * II")
    assert r["error"] is None and r["result_decimal"] == 20 and r["result_roman"] == "XX"
    assert r["consistent"]
    assert r["stages_completed"] == ["lexical", "syntax", "semantic", "codegen", "optimize", "vm"]
    assert r["vm_after"]["steps"] < r["vm_before"]["steps"]


def test_every_phase_has_description_and_output():
    assert [p["key"] for p in PHASE_INFO] == ["lexical", "syntax", "semantic", "codegen", "optimize", "vm"]
    assert all(p["does"] and p["output"] for p in PHASE_INFO)


@pytest.mark.parametrize("src,phase,done", [
    ("IIII + I", "lexical", []),
    ("XII +", "syntax", ["lexical"]),
    ("X / (II - II)", "semantic", ["lexical", "syntax"]),
])
def test_pipeline_stops_at_failing_phase(src, phase, done):
    r = run_pipeline(src)
    assert r["error"]["phase"] == phase and r["stages_completed"] == done
