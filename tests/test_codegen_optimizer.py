import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lexer import tokenize
from parser import Parser
from semantic import analyze
from codegen import generate_code
from optimizer import optimize


def compile_to_asm(text):
    tree = Parser(tokenize(text)).parse()
    value = analyze(tree)
    return generate_code(tree), value


def test_code_generation():
    asm, _ = compile_to_asm("XII + IV * II")
    assert asm == ["PUSH 12", "PUSH 4", "PUSH 2",
                   "POP EBX", "POP EAX", "MUL EAX, EBX", "PUSH EAX",
                   "POP EBX", "POP EAX", "ADD EAX, EBX", "PUSH EAX",
                   "POP EAX", "HLT"]


def test_code_generation_single_number():
    asm, _ = compile_to_asm("XII")
    assert asm == ["PUSH 12", "POP EAX", "HLT"]


def test_brackets_change_the_code_order():
    asm, _ = compile_to_asm("(XII + IV) * II")
    assert asm[:3] == ["PUSH 12", "PUSH 4", "POP EBX"] and "ADD EAX, EBX" in asm[:7]


def test_optimizer_folds_a_chain():
    asm, _ = compile_to_asm("XII + IV * II")
    out, folds = optimize(asm)
    assert out == ["PUSH 20", "POP EAX", "HLT"]
    assert folds == ["PUSH 4, PUSH 2, MUL   ->   PUSH 8", "PUSH 12, PUSH 8, ADD   ->   PUSH 20"]


def test_optimizer_leaves_a_single_number_alone():
    asm, _ = compile_to_asm("XII")
    out, folds = optimize(asm)
    assert out == asm and folds == []


@pytest.mark.parametrize("text", [
    "XII + IV * II", "(XII + IV) * II - X / V", "XII", "M - I - I", "II - X",
    "X / III", "MMMCMXCIX * MMMCMXCIX", "((I + II) * (III + IV)) / II",
])
def test_optimized_assembly_is_the_semantic_value(text):
    # code generation + optimization must agree with semantic analysis
    asm, value = compile_to_asm(text)
    out, _ = optimize(asm)
    assert out == [f"PUSH {value}", "POP EAX", "HLT"]
