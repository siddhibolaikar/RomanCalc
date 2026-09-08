import sys

from errors import CompilerError
from lexer import tokenize
from parser import Parser, tree_to_str, tree_to_dict
from semantic import analyze


def compile_expression(source, verbose=True):
    """Runs `source` through lexical -> syntax -> semantic analysis.

    Returns a dict of intermediate results per stage, so a future
    frontend can display tokens / parse tree / result side by side.
    On any CompilerError, stops at that phase and returns whatever
    stages completed plus an 'error' entry.
    """
    stages = {}
    try:
        tokens = tokenize(source)
        stages["tokens"] = [repr(t) for t in tokens]

        tree = Parser(tokens).parse()
        stages["parse_tree"] = tree_to_str(tree)
        stages["parse_tree_json"] = tree_to_dict(tree)

        value = analyze(tree)
        stages["decimal_result"] = value

        if verbose:
            print("Tokens:")
            for t in stages["tokens"]:
                print(" ", t)
            print("\nParse tree:", stages["parse_tree"])
            print("\nDecimal result:", value)

        return stages

    except CompilerError as e:
        stages["error"] = e.to_dict()
        if verbose:
            pos = f" (position {e.position})" if e.position is not None else ""
            print(f"\n[{e.phase.upper()} ERROR] {e.message}{pos}")
        return stages


if __name__ == "__main__":
    expr = sys.argv[1] if len(sys.argv) > 1 else "XII + IV * II"
    compile_expression(expr)
