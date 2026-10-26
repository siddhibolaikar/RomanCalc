# PHASE 5: CODE OPTIMIZATION
# 1. Constant folding: if both numbers of an operation are known, do the sum
#    now (at compile time). These eight lines ...
#
#        LXI H, 0004H          (4)
#        PUSH H
#        LXI H, 0002H          (2)
#        PUSH H
#        POP D
#        POP H
#        CALL MUL16
#        PUSH H
#
#    ... become two:  LXI H, 0008H  and  PUSH H
# 2. PUSH H followed straight away by POP H does nothing, so both are removed.
# 3. A subroutine that is no longer called is removed.
from codegen import LIBRARY, hex16
from semantic import calculate

OPERATORS = {"CALL ADD16": "+", "CALL SUB16": "-", "CALL MUL16": "*", "CALL DIV16": "/"}


def is_load(line):
    return line.startswith("LXI H, ")


def number_in(line):
    return int(line[7:-1], 16)                    # "LXI H, 000CH" -> 12


def can_fold(eight):
    return (is_load(eight[0]) and eight[1] == "PUSH H"
            and is_load(eight[2]) and eight[3] == "PUSH H"
            and eight[4] == "POP D" and eight[5] == "POP H"
            and eight[6] in OPERATORS
            and eight[7] == "PUSH H")


def optimize(asm):
    out = []
    notes = []
    for line in asm:
        out.append(line)

        if len(out) >= 8 and can_fold(out[-8:]):              # rule 1: constant folding
            a = number_in(out[-8])
            b = number_in(out[-6])
            op = OPERATORS[out[-2]]
            result = calculate(op, a, b)
            notes.append(f"{a} {op} {b} = {result}   ->   LXI H, {hex16(result)}")
            del out[-8:]
            out += ["LXI H, " + hex16(result), "PUSH H"]      # the new number can fold again later

        if out[-2:] == ["PUSH H", "POP H"]:                   # rule 2: this pair does nothing
            notes.append("PUSH H followed by POP H does nothing: removed")
            del out[-2:]

    for name, routine in LIBRARY.items():                     # rule 3: remove unused subroutines
        if routine[0] in out and "CALL " + name not in out:
            start = out.index(routine[0])
            del out[start:start + len(routine)]
            notes.append(f"subroutine {name} is never called: removed")
    return out, notes
