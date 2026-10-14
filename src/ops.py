from errors import CompilerError


def apply_op(op, a, b, phase="semantic"):
    """Single definition of what each operator means, used by the VM at run time.
    Division is integer (floor) division because Roman numerals are integers.
    """
    if op == '+':
        return a + b
    if op == '-':
        return a - b
    if op == '*':
        return a * b
    if op == '/':
        if b == 0:
            raise CompilerError(phase, "division by zero", None, f"{a} / {b}")
        return a // b
    raise CompilerError(phase, f"unknown operator '{op}'")
