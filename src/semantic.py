# PHASE 3: SEMANTIC ANALYSIS (syntax-directed translation)
# Works out a value (val) for every node of the tree, bottom-up,
# and checks things that depend on meaning, such as division by zero.
from errors import CompilerError
from parser import NumeralNode


def calculate(op, a, b):
    """One arithmetic operation. Division is whole-number division."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    return a // b


def analyze(node):
    if isinstance(node, NumeralNode):            # a number's value is itself
        node.val = node.value
        return node.val

    left = analyze(node.left)                    # first the children (bottom-up)
    right = analyze(node.right)

    if node.op == "/" and right == 0:
        raise CompilerError("semantic", "division by zero", node.position, f"{left} / {right}")

    node.val = calculate(node.op, left, right)   # then this node
    return node.val
