# RomanCalc: runs the 5 stages and prints each stage's output in the terminal.
#
#   python main.py "XII + IV * II"          compile one expression
#   python main.py --step "XII + IV * II"   pause after every stage
#   python main.py                          type expressions one after another
import sys

from errors import CompilerError
from lexer import tokenize
from parser import Parser, tree_lines
from semantic import analyze
from codegen import generate_code
from optimizer import optimize
from ai_advisor import explain_error


def compile_source(source):
    """Runs the stages. Returns (stages, assembly). Each stage is (title, what it does, output lines)."""
    stages = []
    asm = None
    try:
        tokens = tokenize(source)
        stages.append(("PHASE 1: LEXICAL ANALYSIS",
                       "Splits the text into tokens and checks every Roman numeral.",
                       [t.show() for t in tokens]))

        tree = Parser(tokens).parse()
        stages.append(("PHASE 2: SYNTAX ANALYSIS",
                       "Checks the grammar and builds the parse tree.",
                       tree_lines(tree)))

        analyze(tree)
        stages.append(("PHASE 3: SEMANTIC ANALYSIS",
                       "Works out the value of every node, from the bottom up.",
                       tree_lines(tree, show_val=True)))

        asm = generate_code(tree)
        stages.append(("PHASE 4: CODE GENERATION",
                       "Walks the tree and writes assembly language.",
                       asm))

        before = len(asm)
        asm, folds = optimize(asm)
        stages.append(("PHASE 5: CODE OPTIMIZATION",
                       "Constant folding: does the sums at compile time.",
                       folds + [f"{before} lines of assembly  ->  {len(asm)} lines"]))

        stages.append(("FINAL OUTPUT: ASSEMBLY PROGRAM",
                       "Result is left in register EAX.",
                       asm))

    except CompilerError as e:
        where = f" (position {e.position})" if e.position is not None else ""
        stages.append((e.phase.upper() + " ERROR", "", [e.message + where]))
        text, who = explain_error(e, source)
        stages.append((f"AI EXPLANATION ({who})", "", [text]))
        asm = None
    return stages, asm


def stage_text(stage):
    title, what, lines = stage
    text = "=" * 62 + "\n" + title + "\n"
    if what:
        text += what + "\n"
    text += "=" * 62 + "\n"
    return text + "".join("  " + line + "\n" for line in lines)


def run(source, step=False):
    stages, asm = compile_source(source)
    for stage in stages:
        print(stage_text(stage))
        if step:
            input("  Press Enter for the next stage...\n")
    if asm:
        with open("output.asm", "w") as f:
            f.write("\n".join(asm) + "\n")
        print("Assembly saved to output.asm\n")


if __name__ == "__main__":
    step = "--step" in sys.argv
    words = [a for a in sys.argv[1:] if a != "--step"]
    if words:
        run(" ".join(words), step)
    else:
        print("RomanCalc  (press Enter on an empty line to quit)")
        while True:
            line = input("\nexpression> ").strip()
            if not line:
                break
            run(line, step)
