from errors import CompilerError
from parser import NumeralNode, BinaryOpNode


def analyze(node):
    """S-attributed SDT: synthesizes `val` on every node bottom-up
    (post-order traversal), and performs semantic checks that can
    only be known at evaluation time (e.g. division by zero).

    Returns the final integer value of the whole expression.
    """
    if isinstance(node, NumeralNode):
        node.val = node.decimal_value
        return node.val

    if isinstance(node, BinaryOpNode):
        left_val = analyze(node.left)
        right_val = analyze(node.right)

        if node.op == '+':
            result = left_val + right_val
        elif node.op == '-':
            result = left_val - right_val
        elif node.op == '*':
            result = left_val * right_val
        elif node.op == '/':
            if right_val == 0:
                raise CompilerError(
                    "semantic",
                    "division by zero",
                    node.position,
                    f"{left_val} / {right_val}",
                )
            result = left_val // right_val  # Roman numerals are integers only
        else:
            raise CompilerError("semantic", f"unknown operator '{node.op}'", node.position)

        node.val = result
        return result

    raise CompilerError("semantic", f"unrecognized parse tree node type {type(node)}", None)


def check_representable(value, position=None):
    """Optional stricter semantic rule: the *result* must itself be a
    representable Roman numeral (1-3999). Not applied by default in
    `analyze()` — call this separately if your design treats
    out-of-range or negative results as a semantic error rather than
    a 'decimal-only output' case.
    """
    if not (1 <= value <= 3999):
        raise CompilerError(
            "semantic",
            f"result {value} cannot be represented as a Roman numeral (must be 1-3999)",
            position,
        )
