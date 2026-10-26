# PHASE 4: CODE GENERATION
# Walks the tree and writes 8085 assembly language.
#
# The 8085 works on bytes, so every number is kept in a 16-bit register
# pair (HL or DE). A register pair holds 0 to 65535.
#
#   LXI H, 000CH   load HL with a number (000CH is 12 in hexadecimal)
#   PUSH H         put HL on the stack
#   POP D          take the top of the stack into DE
#   POP H          take the top of the stack into HL
#   CALL ADD16     HL = HL + DE   (likewise SUB16, MUL16, DIV16)
#   HLT            stop. The answer is in HL
from parser import NumeralNode

ROUTINE = {"+": "ADD16", "-": "SUB16", "*": "MUL16", "/": "DIV16"}

# The 8085 has no multiply or divide instruction, so every operation is a small
# subroutine written in 8085 assembly. Each one takes HL (left) and DE (right)
# and leaves the answer in HL.
LIBRARY = {
    "ADD16": [
        "ADD16:",
        "DAD D          ; HL = HL + DE",
        "RET",
    ],
    "SUB16": [
        "SUB16:",
        "MOV A, L       ; low bytes:  L - E",
        "SUB E",
        "MOV L, A",
        "MOV A, H       ; high bytes: H - D - borrow",
        "SBB D",
        "MOV H, A",
        "RET",
    ],
    "MUL16": [
        "MUL16:",
        "MOV B, H       ; BC = the left number",
        "MOV C, L",
        "LXI H, 0000H   ; HL = 0, the running total",
        "MULLP:",
        "MOV A, D       ; DE counts how many times to add",
        "ORA E          ; DE = 0 ?",
        "RZ             ; yes: finished",
        "DAD B          ; HL = HL + BC",
        "DCX D          ; DE = DE - 1",
        "JMP MULLP",
    ],
    "DIV16": [
        "DIV16:",
        "LXI B, 0000H   ; BC = quotient, starts at 0",
        "DIVLP:",
        "MOV A, L       ; is HL - DE negative?",
        "SUB E",
        "MOV A, H",
        "SBB D",
        "JC DIVEND      ; yes: finished",
        "MOV A, L       ; no: HL = HL - DE",
        "SUB E",
        "MOV L, A",
        "MOV A, H",
        "SBB D",
        "MOV H, A",
        "INX B          ; quotient = quotient + 1",
        "JMP DIVLP",
        "DIVEND:",
        "MOV H, B       ; HL = quotient",
        "MOV L, C",
        "RET",
    ],
}


def hex16(n):
    """A number in 8085 hexadecimal: 12 -> 000CH, 65528 -> 0FFF8H (a letter cannot come first)."""
    text = f"{n:04X}H"
    return "0" + text if text[0] in "ABCDEF" else text


def generate_code(tree):
    program = ["LXI SP, 0FFFFH"]                  # the stack starts at the top of memory
    program += gen(tree)
    program += ["POP H", "HLT"]                   # the final answer is left in HL
    for name, routine in LIBRARY.items():         # add the subroutines the program calls
        if "CALL " + name in program:
            program += routine
    return program


def gen(node):
    if isinstance(node, NumeralNode):
        return ["LXI H, " + hex16(node.value), "PUSH H"]

    return (gen(node.left)                        # code for the left side
            + gen(node.right)                     # code for the right side
            + ["POP D",                           # right number into DE
               "POP H",                           # left number into HL
               "CALL " + ROUTINE[node.op],        # HL = HL op DE
               "PUSH H"])                         # keep the result on the stack
