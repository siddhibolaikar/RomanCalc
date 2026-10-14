"""Phase 4 - Code Generation (parse tree -> stack-machine program) + VM.

A post-order walk of the parse tree gives exactly the order a stack machine
needs: push both operands, then apply the operator.

    XII + IV * II   ->   PUSH 12 ; PUSH 4 ; PUSH 2 ; MUL ; ADD ; PRINT ; HALT

The program ends with PRINT (output the top of stack) and HALT.
"""
from errors import CompilerError
from parser import NumeralNode
from ops import apply_op

OPCODES = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV'}
BIN_OPS = {v: k for k, v in OPCODES.items()}     # 'ADD' -> '+'


def generate_code(tree):
    code = []

    def emit(node):
        if isinstance(node, NumeralNode):
            code.append(("PUSH", node.decimal_value))
            return
        emit(node.left)
        emit(node.right)
        code.append((OPCODES[node.op],))

    emit(tree)
    code.append(("PRINT",))
    code.append(("HALT",))
    return code


def fmt(ins):
    return " ".join(str(p) for p in ins)


class VM:
    """Tiny stack machine: executes instructions one at a time and records a trace."""

    def run(self, code):
        stack, trace, output = [], [], None
        pc = 0
        while pc < len(code):
            ins = code[pc]
            op = ins[0]
            if op == "PUSH":
                stack.append(ins[1])
            elif op in BIN_OPS:
                b = self._pop(stack, ins)
                a = self._pop(stack, ins)
                stack.append(apply_op(BIN_OPS[op], a, b, phase="runtime"))
            elif op == "PRINT":
                output = self._pop(stack, ins)
            elif op == "HALT":
                trace.append({"pc": pc, "instr": fmt(ins), "stack": list(stack)})
                break
            else:
                raise CompilerError("runtime", f"unknown instruction {op}")
            trace.append({"pc": pc, "instr": fmt(ins), "stack": list(stack)})
            pc += 1
        return {"output": output, "trace": trace, "steps": len(trace)}

    @staticmethod
    def _pop(stack, ins):
        if not stack:
            raise CompilerError("runtime", f"stack underflow at '{fmt(ins)}'")
        return stack.pop()
