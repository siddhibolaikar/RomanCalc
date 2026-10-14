"""
demo.py - walks through every compiler phase ONE AT A TIME, pausing between
phases. For each phase it prints what the phase does, then its output.

    python demo.py "(XII + IV) * II"
    python demo.py                       # default expression
"""
import sys
from errors import CompilerError
from lexer import tokenize
from parser import Parser, tree_to_str, tree_to_dict
from semantic import analyze
from codegen import generate_code, VM, fmt
from optimizer import optimize
from pipeline import PHASE_INFO, to_roman

INFO = {p["key"]: p for p in PHASE_INFO}


def header(key):
    p = INFO[key]
    print(f"\n{'=' * 68}\n  {p['name'].upper()}\n{'=' * 68}")
    print(f"  What it does : {p['does']}")
    print(f"  Output       : {p['output']}\n")


def pause():
    input("\nPress Enter for the next phase...")


def outline(node, indent=0, show_val=False):
    pad = "  " * indent
    d = tree_to_dict(node)
    tail = f"   -> val = {d['val']}" if show_val else ""
    if d["type"] == "Numeral":
        print(f"{pad}Numeral {d['roman']} (= {d['value']}){tail}")
    else:
        print(f"{pad}Operator {d['op']}{tail}")
        outline(node.left, indent + 1, show_val)
        outline(node.right, indent + 1, show_val)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "XII + IV * II"
    print(f"{'=' * 68}\n  INPUT: {source}\n{'=' * 68}")
    try:
        header("lexical")
        tokens = tokenize(source)
        for t in tokens:
            print("  ", t)
        pause()

        header("syntax")
        tree = Parser(tokens).parse()
        outline(tree)
        print("\n  bracketed:", tree_to_str(tree))
        pause()

        header("semantic")
        value = analyze(tree)
        outline(tree, show_val=True)
        print("\n  value of the expression =", value)
        pause()

        header("codegen")
        code = generate_code(tree)
        for ins in code:
            print("  ", fmt(ins))
        pause()

        header("optimize")
        opt, log = optimize(code)
        for line in log:
            print("   fold:", line)
        print("\n  optimized program:")
        for ins in opt:
            print("  ", fmt(ins))
        print(f"\n  {len(code)} instructions -> {len(opt)} instructions")
        pause()

        header("vm")
        run = VM().run(opt)
        for s in run["trace"]:
            print(f"   pc={s['pc']:<2} {s['instr']:<10} stack={s['stack']}")
        roman, note = to_roman(run["output"])
        print(f"\n  RESULT: {run['output']}  =  {roman or 'n/a (' + note + ')'}")
    except CompilerError as e:
        pos = f" (position {e.position})" if e.position is not None else ""
        print(f"\n[{e.phase.upper()} ERROR] {e.message}{pos}")


if __name__ == "__main__":
    main()
