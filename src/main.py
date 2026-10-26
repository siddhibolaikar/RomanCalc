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
from ai_advisor import explain_error, suggest_fixes


def run_phases(source):
    """Runs the five phases. Returns (stages, assembly, error). error is None if everything worked.
    Each stage is (title, what it does, output lines)."""
    stages = []
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
                       "Walks the tree and writes 8085 assembly language.",
                       asm))

        before = len(asm)
        asm, notes = optimize(asm)
        stages.append(("PHASE 5: CODE OPTIMIZATION",
                       "Constant folding (sums done at compile time) and removal of code that is no longer needed.",
                       notes + [f"{before} lines of assembly  ->  {len(asm)} lines"]))

        stages.append(("FINAL OUTPUT: 8085 ASSEMBLY PROGRAM",
                       "The result is left in register pair HL.",
                       asm))
        return stages, asm, None

    except CompilerError as e:
        return stages, None, e


def compile_source(source):
    """Runs the phases. If there is an error, adds the AI explanation and a verified fix.
    Returns (stages, assembly); assembly is None when the input has an error."""
    stages, asm, error = run_phases(source)
    if error:
        where = f" (position {error.position})" if error.position is not None else ""
        stages.append((error.phase.upper() + " ERROR", "", [error.message + where]))
        text, who = explain_error(error, source)
        stages.append((f"AI EXPLANATION ({who})", "", [text]))
        stages += fix_stages(source, error)
    return stages, asm


def fix_stages(source, error):
    """The AI proposes a corrected input. The compiler runs it through all five phases
    and accepts it only if every phase passes (AI proposes, compiler decides)."""
    rejected = []
    for candidate, who in suggest_fixes(error, source):
        _, fixed_asm, fixed_error = run_phases(candidate)
        if fixed_error is None:                                  # the compiler accepted it
            return [(f"SUGGESTED FIX ({who})",
                     "The compiler checked this input by running all five phases on it.",
                     rejected + [f"{source}   ->   {candidate}"]),
                    ("VERIFIED: ALL 5 PHASES PASSED",
                     "8085 program for the corrected input. The result is left in register pair HL.",
                     fixed_asm)]
        rejected.append(f"{who} suggested '{candidate}', but the compiler rejected it: {fixed_error.message}")
    return [("NO VERIFIED FIX", "",
             rejected + ["No corrected input that passes all five phases was found."])]


def stage_text(stage):
    title, what, lines = stage
    text = "=" * 62 + "\n" + title + "\n"
    if what:
        text += what + "\n"
    text += "=" * 62 + "\n"
    for line in lines:
        pad = "  " if line.endswith(":") else "    "     # labels stand out from instructions
        text += pad + line + "\n"
    return text


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
