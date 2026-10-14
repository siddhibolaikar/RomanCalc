"""Phase 5 - Code Optimization: constant folding on the stack program.

In postfix (stack) code, the pattern

        PUSH a ; PUSH b ; <OP>

always computes a constant, so it can be replaced by  PUSH (a OP b)  at
compile time. Folded results are PUSH instructions too, so they can fold
again with whatever follows - chains of operations collapse in one pass.

    PUSH 12 ; PUSH 4 ; PUSH 2 ; MUL ; ADD
        -> PUSH 12 ; PUSH 8 ; ADD          (4 * 2 folded)
        -> PUSH 20                         (12 + 8 folded)
"""
from codegen import BIN_OPS
from ops import apply_op


def optimize(code):
    """Returns (optimized_code, log) where log lists every fold performed."""
    out, log = [], []
    for ins in code:
        if (ins[0] in BIN_OPS and len(out) >= 2
                and out[-1][0] == "PUSH" and out[-2][0] == "PUSH"):
            b = out.pop()[1]
            a = out.pop()[1]
            value = apply_op(BIN_OPS[ins[0]], a, b, phase="optimization")
            out.append(("PUSH", value))
            log.append(f"PUSH {a} ; PUSH {b} ; {ins[0]}   ->   PUSH {value}")
        else:
            out.append(ins)
    return out, log
