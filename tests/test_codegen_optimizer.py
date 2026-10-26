import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import pytest
from lexer import tokenize
from parser import Parser
from semantic import analyze
from codegen import generate_code, hex16, LIBRARY
from optimizer import optimize
from sim8085 import run8085


def compile_to_asm(text):
    tree = Parser(tokenize(text)).parse()
    value = analyze(tree)
    return generate_code(tree), value


# ---------------- hexadecimal ----------------
@pytest.mark.parametrize("n,text", [(12, "000CH"), (0, "0000H"), (3999, "0F9FH"), (4096, "1000H"), (65535, "0FFFFH")])
def test_hex16(n, text):
    assert hex16(n) == text


# ---------------- code generation ----------------
def test_code_generation_main_program():
    asm, _ = compile_to_asm("XII + IV * II")
    main_program = asm[:asm.index("HLT") + 1]
    assert main_program == ["LXI SP, 0FFFFH",
                            "LXI H, 000CH", "PUSH H",
                            "LXI H, 0004H", "PUSH H",
                            "LXI H, 0002H", "PUSH H",
                            "POP D", "POP H", "CALL MUL16", "PUSH H",
                            "POP D", "POP H", "CALL ADD16", "PUSH H",
                            "POP H", "HLT"]


def test_only_the_called_subroutines_are_added():
    asm, _ = compile_to_asm("XII + IV * II")
    assert asm[asm.index("HLT") + 1:] == LIBRARY["ADD16"] + LIBRARY["MUL16"]


def test_single_number_needs_no_subroutine():
    asm, _ = compile_to_asm("XII")
    assert asm == ["LXI SP, 0FFFFH", "LXI H, 000CH", "PUSH H", "POP H", "HLT"]


# ---------------- optimization ----------------
def test_optimizer_folds_a_chain_and_cleans_up():
    asm, _ = compile_to_asm("XII + IV * II")
    out, notes = optimize(asm)
    assert out == ["LXI SP, 0FFFFH", "LXI H, 0014H", "HLT"]
    assert notes[:2] == ["4 * 2 = 8   ->   LXI H, 0008H", "12 + 8 = 20   ->   LXI H, 0014H"]
    assert "subroutine MUL16 is never called: removed" in notes


def test_single_number_loses_only_the_push_pop_pair():
    asm, _ = compile_to_asm("XII")
    out, notes = optimize(asm)
    assert out == ["LXI SP, 0FFFFH", "LXI H, 000CH", "HLT"]
    assert notes == ["PUSH H followed by POP H does nothing: removed"]


def test_optimizer_makes_the_program_shorter():
    asm, _ = compile_to_asm("(XII + IV) * II - X / V")
    out, _ = optimize(asm)
    assert len(out) == 3 < len(asm)


EXPRESSIONS = [
    "XII + IV * II", "(XII + IV) * II - X / V", "XII", "M - I - I", "X / III",
    "MMMCMXCIX + MMMCMXCIX", "MMMCMXCIX / I", "II * MMMCMXCIX", "X - X", "((I + II) * (III + IV)) / II",
    "X / (II + III) * V", "MCMXCIX - MCMXCIX + I",
]


@pytest.mark.parametrize("text", EXPRESSIONS)
def test_unoptimized_8085_program_gives_the_right_answer(text):
    # run the generated 8085 program (including the MUL16 / DIV16 subroutines) on the simulator
    asm, value = compile_to_asm(text)
    assert run8085(asm) == value


@pytest.mark.parametrize("text", EXPRESSIONS)
def test_optimized_8085_program_gives_the_right_answer(text):
    asm, value = compile_to_asm(text)
    out, _ = optimize(asm)
    assert out == ["LXI SP, 0FFFFH", "LXI H, " + hex16(value), "HLT"]
    assert run8085(out) == value
