"""
demo.py — walks through each compiler phase ONE AT A TIME, pausing
between them, so you can narrate what just happened before moving on.

Usage:
    python demo.py "XII + IV * II"
    python demo.py                      # uses a default expression
"""
import sys
from errors import CompilerError
from lexer import tokenize
from parser import Parser, tree_to_str, tree_to_dict
from semantic import analyze


def pause(msg="\nPress Enter to continue to the next phase..."):
    input(msg)


def print_tree_indented(node, indent=0):
    """Pretty-print the parse tree as an indented outline instead of
    one bracketed line — easier to read out loud during a demo."""
    pad = "  " * indent
    d = tree_to_dict(node)
    if d["type"] == "Numeral":
        print(f"{pad}Numeral: {d['roman']} = {d['value']}")
    else:
        print(f"{pad}BinaryOp: {d['op']}")
        print_tree_indented(node.left, indent + 1)
        print_tree_indented(node.right, indent + 1)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else "XII + IV * II"

    print("=" * 60)
    print(f"  INPUT EXPRESSION:  {source}")
    print("=" * 60)

    # ---------------- PHASE 1: LEXICAL ANALYSIS ----------------
    print("\n--- PHASE 1: LEXICAL ANALYSIS ---")
    print("Scanning source into tokens, validating every Roman numeral...\n")
    try:
        tokens = tokenize(source)
    except CompilerError as e:
        print(f"[LEXICAL ERROR] {e.message} (position {e.position})")
        return

    for t in tokens:
        print(f"  {t}")
    print(f"\n=> {len(tokens)} tokens produced.")
    pause()

    # ---------------- PHASE 2: SYNTAX ANALYSIS ----------------
    print("\n--- PHASE 2: SYNTAX ANALYSIS ---")
    print("Running recursive descent parser over the token stream...\n")
    try:
        tree = Parser(tokens).parse()
    except CompilerError as e:
        print(f"[SYNTAX ERROR] {e.message} (position {e.position})")
        return

    print("Parse tree (indented):")
    print_tree_indented(tree)
    print(f"\nParse tree (bracketed form): {tree_to_str(tree)}")
    pause()

    # ---------------- PHASE 3: SDT / SEMANTIC ANALYSIS ----------------
    print("\n--- PHASE 3: SDT / SEMANTIC ANALYSIS ---")
    print("Evaluating the tree bottom-up, checking for semantic errors...\n")
    try:
        value = analyze(tree)
    except CompilerError as e:
        print(f"[SEMANTIC ERROR] {e.message} (position {e.position})")
        return

    print("Each node's synthesized 'val' after evaluation:")
    print_annotated_tree(tree)
    print(f"\n=> FINAL DECIMAL RESULT: {value}")


def print_annotated_tree(node, indent=0):
    pad = "  " * indent
    d = tree_to_dict(node)
    if d["type"] == "Numeral":
        print(f"{pad}{d['roman']}  ->  val = {node.val}")
    else:
        print(f"{pad}{d['op']}  ->  val = {node.val}")
        print_annotated_tree(node.left, indent + 1)
        print_annotated_tree(node.right, indent + 1)


if __name__ == "__main__":
    main()