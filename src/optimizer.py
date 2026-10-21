# PHASE 5: CODE OPTIMIZATION (constant folding)
# If both numbers of an operation are already known, do the sum now
# (at compile time) instead of leaving it for the machine.
#
#   PUSH 4
#   PUSH 2
#   POP EBX
#   POP EAX        --->   PUSH 8
#   MUL EAX, EBX
#   PUSH EAX
from semantic import calculate

OPERATORS = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/"}


def is_number_push(line):
    parts = line.split()                          # e.g. ["PUSH", "12"]
    return len(parts) == 2 and parts[0] == "PUSH" and parts[1].lstrip("-").isdigit()


def can_fold(six):
    return (is_number_push(six[0])                # PUSH a
            and is_number_push(six[1])            # PUSH b
            and six[2] == "POP EBX"
            and six[3] == "POP EAX"
            and six[4].split()[0] in OPERATORS    # ADD / SUB / MUL / DIV
            and six[5] == "PUSH EAX")


def optimize(asm):
    out = []
    folds = []
    for line in asm:
        out.append(line)
        if len(out) >= 6 and can_fold(out[-6:]):          # do the last 6 lines form a fold?
            six = out[-6:]
            a = int(six[0].split()[1])
            b = int(six[1].split()[1])
            result = calculate(OPERATORS[six[4].split()[0]], a, b)
            folds.append(f"PUSH {a}, PUSH {b}, {six[4].split()[0]}   ->   PUSH {result}")
            del out[-6:]
            out.append(f"PUSH {result}")           # the new PUSH can fold again later
    return out, folds
